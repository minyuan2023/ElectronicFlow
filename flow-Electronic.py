import sys
import subprocess
import os
import concurrent.futures


def run_command(command, cwd=None):
    """同步执行命令，若返回码非0则退出。"""
    print(f"Running: {' '.join(command)} (cwd: {cwd if cwd else os.getcwd()})")
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        print(f"Command {' '.join(command)} failed with return code {result.returncode}.")
        sys.exit(result.returncode)


def main():
    # 参数格式：MAT net_charge adsorbate1 [adsorbate2 ...]
    if len(sys.argv) < 4:
        print("Usage: python flow-Electronic.py MAT net_charge adsorbate1 [adsorbate2 ...]")
        sys.exit(1)

    MAT = sys.argv[1]
    net_charge = sys.argv[2]
    adsorbates = sys.argv[3:]

    # --- 第一步：调用脚本（Bader 分析） ---
    print("=== Running Bader Analysis (script8: ORRbader.py) ===")
    run_command(["python", "ORRbader.py", MAT] + adsorbates)

    # --- 第二步：调用脚本（差分电荷密度计算） ---
    print("=== Running Charge Density Difference Analysis (script9: ORRcdd.py) ===")
    run_command(["python", "ORRcdd.py", MAT] + adsorbates)

    # --- 第三步：电子结构流程（脚本4） ---
    # 对每个 adsorbate并行执行电子结构流程任务
    print("=== Running Electronic Structure Flow (script4) for each adsorbate in parallel ===")

    def process_ads(ads):
        print(f"Processing electronic structure for adsorbate: {ads}")
        # 脚本4（电子结构流程）要求参数顺序：MAT net_charge adsorbate
        run_command(["python", "script4.py", MAT, net_charge, ads])

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_ads, ads) for ads in adsorbates]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    print("All tasks have been successfully completed.")


if __name__ == "__main__":
    main()
