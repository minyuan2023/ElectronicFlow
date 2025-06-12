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
    DIRS = sys.argv[2:]
else:
    DIRS = ["OOH", "OH", "O", "Support"]

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

# 计算 Bader 电荷
def generate_bader(identifier):  # identifier 例如 "Support", "OOH", "OH", "O"
    input_path = os.path.join('..', identifier, MAT, 'CONTCAR')
    structure = Structure.from_file(input_path)
    output_path = os.path.join('..', identifier, '3-bader', MAT)
    kpoints_set = {'reciprocal_density': 100}
    incar_set = {
        'IBRION': -1, 'LAECHG': 'True', 'NSW': 0, 'LCHARG': True,
        'ALGO': "Normal", 'EDIFFG': -0.02, 'EDIFF': 0.00001, 'ENCUT': 500,
        'ISMEAR': 0, 'ISPIN': 2, 'ICHARG': 2, 'LWAVE': False, 'PREC': 'Normal',
        'NCORE': 4, 'ISIF': 1, 'NELM': 200, 'LDAU': False
    }
    Relax = MITRelaxSet(structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
    Relax.write_input(output_path)
    log_info(f"Bader input files written successfully to {output_path}.")

if __name__ == "__main__":
    # 生成 Bader 输入文件
    for DIR in DIRS:
        with change_directory(os.path.join("..", DIR)):
            generate_bader(DIR)
    # 提交 Bader 计算任务
    runjob_ids = []
    for DIR in DIRS:
        outcar_path = os.path.join("..", DIR, "3-bader", MAT, "OUTCAR")
        try:
            if not os.path.isfile(outcar_path):
                raise FileNotFoundError(f"File {outcar_path} not found")
            check_output = subprocess.check_output(["grep", "-q", "Total CPU time", outcar_path],
                                                   stderr=subprocess.STDOUT).decode()
            log_info(f"Calculation for 3-bader {DIR} {MAT} successfully completed.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            target_directory = os.path.join("..", DIR, '3-bader')
            with change_directory(target_directory):
                log_info(f"Submitting 3-bader {DIR} {MAT}.")
                runjob_id = submit_job(MAT)
                if runjob_id:
                    runjob_ids.append(runjob_id)
    for runjob_id in runjob_ids:
        wait_for_job_completion(runjob_id)
    # 分析计算结果
    for DIR in DIRS:
        try:
            check_output = subprocess.check_output(
                ["grep", "-q", "Total CPU time", f"../{DIR}/3-bader/{MAT}/OUTCAR"],
                stderr=subprocess.STDOUT
            ).decode()
            log_info(f"Analyzing 3-bader {DIR} {MAT}.")
            with change_directory(os.path.join("..", DIR, '3-bader', MAT)):
                subprocess.check_call(["chgsum.pl", "AECCAR0", "AECCAR2"])
                subprocess.check_call(["bader", "CHGCAR", "-ref", "CHGCAR_sum"])
        except subprocess.CalledProcessError as e:
            log_info(f"Error: {e.output.decode()}")
