import numpy as np
import os
import subprocess
import time
import datetime
import sys
import glob
import re
from contextlib import contextmanager
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.io.vasp import Poscar
from pymatgen.core import Lattice, Molecule, Structure
from pymatgen.core.surface import generate_all_slabs
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.io.vasp.sets import MITRelaxSet
from pymatgen.io.vasp.sets import MPNonSCFSet
from pymatgen.io.vasp.inputs import Kpoints
import warnings

warnings.simplefilter("ignore")

# 定义任务状态枚举
TASK_STATUS = {
    "NOT_EXIST": "not_exist",
    "NOT_EXECUTED": "not_executed",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
    "SUCCESS": "success",
    "FAILED": "failed",
    "RETRY": "retry",
    "MAX_RETRY_REACHED": "max_retry_reached"
}

RCHECK_SCRIPT = "rcheck.sh"
RELAX2_SCRIPT = "std-subvasp.sh"

MAT = sys.argv[1]  # MAT，例如 Fe, FePc, Fe2O3, Fe-MOF 等
if len(sys.argv) > 2:
    ADS = sys.argv[2:]
else:
    ADS = ["OOH", "OH", "O", "Support"]

def log_info(message):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: {message}")

def log_error(message):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {message}", file=sys.stderr)

def error_exit(message):
    log_error(message)
    exit(1)

@contextmanager
def change_directory(destination):
    original_dir = os.getcwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(original_dir)

def submit_job(identifier):
    try:
        job_output = subprocess.check_output([RELAX2_SCRIPT, identifier]).decode()
        job_id_match = re.search(r'job (\d+)', job_output)
        if job_id_match:
            job_id = job_id_match.group(1)
            log_info(f"Submitted job {job_id} for {identifier}.")
            return job_id
        else:
            log_error(f"Error: Failed to find job ID in output: {job_output}")
            return
    except subprocess.CalledProcessError as e:
        error_exit(f"Error: Failed to submit job for {identifier}. Details: {e}")

def wait_for_job_completion(job_id):
    log_info(f"Waiting for job {job_id} to complete...")
    while True:
        try:
            job_status = subprocess.check_output(['squeue', '-j', job_id], stderr=subprocess.DEVNULL).decode()
            if job_id not in job_status:
                log_info(f"Job {job_id} has completed.")
                break
        except subprocess.CalledProcessError:
            break
        log_info(f"Job {job_id} is still running...")
        time.sleep(300)

# 生成差分电荷密度（CDD）输入文件
def generate_cdd(identifier):
    # Step 1：读取优化好的催化剂结构
    support_path = os.path.join('..', 'Support', MAT, 'CONTCAR')
    structure = Structure.from_file(support_path)
    # Step 2：读取吸附物结构（从 xyz 文件读取）
    ads_path = os.path.expanduser(os.path.join('..', 'Support', identifier + '.xyz'))
    ads_name = Molecule.from_file(ads_path)
    # Step 3：将吸附物平移到合适位置并添加到结构中
    cart_coords = structure.cart_coords
    z_coords = cart_coords[:, 2]
    eps = 0.5
    labels = np.full(len(z_coords), -1, dtype=int)
    current_label = 0
    for i in range(len(z_coords)):
        if labels[i] == -1:
            labels[i] = current_label
            for j in range(i + 1, len(z_coords)):
                if labels[j] == -1 and abs(z_coords[i] - z_coords[j]) <= eps:
                    labels[j] = current_label
            current_label += 1
    layers = []
    for label in np.unique(labels):
        layer_indices = np.where(labels == label)[0]
        layers.append(layer_indices)
    layers = sorted(layers, key=lambda layer: np.mean(z_coords[layer]), reverse=True)
    num_layers = len(layers)
    num_top_layers = 3
    if num_layers <= num_top_layers:
        top_layers = layers[:num_layers]
    else:
        top_layers = layers[:num_top_layers]
    surface_properties = ["subsurface"] * len(structure.sites)
    for layer in top_layers:
        for index in layer:
            surface_properties[index] = "surface"
    structure.add_site_property("surface_properties", surface_properties)
    site_index = 0
    site_coords = structure[site_index].coords
    ads_position = ads_name[0].coords
    translation_to_origin = -np.array(ads_position)
    ads_name.translate_sites(list(range(len(ads_name))), translation_to_origin)
    adjusted_coords = [site_coords[0], site_coords[1], site_coords[2] + 2.4]
    translation_vector = adjusted_coords
    ads_name.translate_sites(list(range(len(ads_name))), translation_vector)
    for site in ads_name:
        structure.append(
            site.specie,
            site.coords,
            coords_are_cartesian=True,
            properties={"surface_properties": "adsorbate"}
        )
    structure = structure.get_sorted_structure()
    # Step 4：从复合结构中分离出催化剂与吸附物结构（利用 site_properties）
    bader_path = os.path.join('..', identifier, '3-bader', MAT, 'CONTCAR')
    bader_structure = Structure.from_file(bader_path)
    support_index = []
    adsorbate_index = []
    group = structure.site_properties["surface_properties"]
    for i, prop in enumerate(group):
        if prop in {"surface", "subsurface"}:
            support_index.append(i)
        elif prop == "adsorbate":
            adsorbate_index.append(i)
    support_sites = [bader_structure[i] for i in support_index]
    support_structure = Structure.from_sites(support_sites)
    adsorbate_sites = [bader_structure[i] for i in adsorbate_index]
    adsorbate_structure = Structure.from_sites(adsorbate_sites)
    kpoints_set = {'reciprocal_density': 100}
    incar_set = {
        'IBRION': -1, 'LAECHG': 'True', 'NSW': 0, 'LCHARG': True,
        'ALGO': "Normal", 'EDIFFG': -0.02, 'EDIFF': 0.00001, 'ENCUT': 500,
        'ISMEAR': 0, 'ISPIN': 2, 'ICHARG': 2, 'LWAVE': False, 'PREC': 'Normal',
        'NCORE': 4, 'ISIF': 1, 'NELM': 200, 'LDAU': False
    }
    support_bader_path = os.path.join('..', identifier, '3-bader', MAT, 'support')
    support_Relax = MITRelaxSet(support_structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
    support_Relax.write_input(support_bader_path)
    adsorbate_bader_path = os.path.join('..', identifier, '3-bader', MAT, 'adsorbate')
    adsorbate_Relax = MITRelaxSet(adsorbate_structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
    adsorbate_Relax.write_input(adsorbate_bader_path)
    log_info("Charge input files have been written successfully.")

if __name__ == "__main__":
    # 生成差分电荷密度输入文件
    for ads in ADS:
        with change_directory(os.path.join("..", ads)):
            generate_cdd(ads)
    # 提交差分电荷密度计算任务
    runjob_ids = []
    DIRS = ["support", "adsorbate"]
    for ads in ADS:
        for dir in DIRS:
            outcar_path = os.path.join("..", ads, "3-bader", MAT, dir, "OUTCAR")
            try:
                if not os.path.isfile(outcar_path):
                    raise FileNotFoundError(f"File {outcar_path} not found")
                check_output = subprocess.check_output(["grep", "-q", "Total CPU time", outcar_path],
                                                       stderr=subprocess.STDOUT).decode()
                log_info("Calculation for charge density difference successfully completed.")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                target_directory = os.path.join("..", ads, '3-bader', MAT)
                with change_directory(target_directory):
                    log_info("Submitting support.")
                    runjob_id = submit_job(dir)
                    if runjob_id:
                        runjob_ids.append(runjob_id)
    for runjob_id in runjob_ids:
        wait_for_job_completion(runjob_id)
    # 分析计算结果
    for ads in ADS:
        log_info("Analyzing charge density difference.")
        with change_directory(os.path.join("..", ads, '3-bader', MAT)):
            command = 'echo -e "314\nCHGCAR support/CHGCAR adsorbate/CHGCAR\n" | vaspkit'
            subprocess.check_call(command, shell=True)
