import os
import sys
import subprocess
import re
import time
import concurrent.futures


def run_command(command, cwd=None):
    """
    同步执行命令（适用于 NELECT.py、upik0.py、upik.py 等）。
    如果返回码非 0，则退出整个脚本。
    """
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        print(f"Command {' '.join(command)} failed with return code {result.returncode}.")
        sys.exit(result.returncode)


def submit_and_wait(command, cwd=None):
    """
    提交作业并等待作业完成。用于调用 gam-subvasp.sh 和 std-subvasp.sh，
    要求输出中包含形如 "job <jobid>" 的作业号。
    """
    try:
        output = subprocess.check_output(command, cwd=cwd, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        print(f"Command {' '.join(command)} failed with error: {e}")
        sys.exit(e.returncode)
    job_match = re.search(r'job\s+(\d+)', output, re.IGNORECASE)
    if job_match:
        job_id = job_match.group(1)
        wait_for_job_completion(job_id)
    else:
        print("Could not parse job id from output.")
        sys.exit(1)


def wait_for_job_completion(job_id):
    """
    循环检查 squeue 中是否还有该作业，直到作业完成。
    仅输出最少信息。
    """
    while True:
        try:
            job_status = subprocess.check_output(['squeue', '-j', job_id], universal_newlines=True)
        except subprocess.CalledProcessError:
            break
        if job_id not in job_status:
            break
        time.sleep(60)


def get_four_dos_dir(adsorbate):
    """
    根据 adsorbate 参数构造 4-dos 目录路径，
    假定该目录位于当前脚本所在目录的父目录下：parent/adsorbate/4-dos
    """
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    four_dos_dir = os.path.join(parent_dir, adsorbate, "4-dos")
    if not os.path.isdir(four_dos_dir):
        os.makedirs(four_dos_dir, exist_ok=True)
    return four_dos_dir


def process_adsorbate(MAT, net_charge, adsorbate):
    """
    针对单个 adsorbate 执行全部流程：
    1. 调用 NELECT.py
    2. 调用 upik0.py
    3. 在对应的 4-dos 目录下提交 gam-subvasp.sh MAT，并等待作业完成
    4. 调用 upik.py
    5. 在对应的 4-dos 目录下提交 std-subvasp.sh MAT，并等待作业完成
    """
    print(f"Processing adsorbate: {adsorbate}")
    run_command(["python", "NELECT.py", MAT, adsorbate, net_charge])
    run_command(["python", "upik0.py", MAT, adsorbate])
    four_dos_dir = get_four_dos_dir(adsorbate)
    submit_and_wait([os.path.expanduser("~/bin/gam-subvasp.sh"), MAT], cwd=four_dos_dir)
    run_command(["python", "upik.py", MAT, adsorbate])
    submit_and_wait([os.path.expanduser("~/bin/std-subvasp.sh"), MAT], cwd=four_dos_dir)
    print(f"Finished processing adsorbate: {adsorbate}")


def main():
    # 参数顺序：MAT net_charge adsorbate1 [adsorbate2 ...]
    if len(sys.argv) < 4:
        print("Usage: python script4.py MAT net_charge adsorbate1 [adsorbate2 ...]")
        sys.exit(1)
    MAT = sys.argv[1]
    net_charge = sys.argv[2]
    adsorbates = sys.argv[3:]

    # 使用并行执行各 adsorbate 的流程
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_adsorbate, MAT, net_charge, ads) for ads in adsorbates]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                print("An error occurred during processing:", exc)
                sys.exit(1)
    print("All tasks have been successfully completed.")


if __name__ == "__main__":
    main()
