import os
import re
import sys
import shutil
import argparse
import math

# 定义需要修改的参数（不包括 NBANDS）
params_to_modify = {
    "NSW": "0",
    "ICHARG": "11",
    "LCHARG": "False"
}

# 定义需要添加的新参数（不包括 NBANDS，由于 NBANDS 需要根据 NELECT 动态计算）
params_to_add = {
    "LAECHG": "False",
    "LASPH": "True",
    "LVHAR": "False",
    "NEDOS": "2001",
    "KPOINT_BSE": "-1 0 0 0"
}

def backup_file(file_path):
    backup_path = file_path + ".bak"
    shutil.copy(file_path, backup_path)
    print(f"已备份文件到: {backup_path}")

def calculate_nbands(lines):
    """
    从 INCAR 内容中读取 NELECT 的值，并计算 NBANDS：
    NBANDS 为大于 (NELECT * 0.6) 且能被4整除的最小整数。
    """
    for line in lines:
        m = re.search(r'^NELECT\s*=\s*(\S+)', line, re.IGNORECASE)
        if m:
            try:
                nelect = float(m.group(1))
                base_value = nelect * 0.6
                nbands = math.ceil(base_value)
                while nbands % 4 != 0 or nbands <= base_value:
                    nbands += 1
                return nbands
            except Exception as e:
                print(f"计算 NBANDS 时出错: {e}")
                return None
    print("在 INCAR 文件中未找到 NELECT 参数。")
    return None

def edit_incar(incar_path):
    with open(incar_path, 'r') as file:
        lines = file.readlines()

    # 修改已存在的参数
    for i, line in enumerate(lines):
        for param, value in params_to_modify.items():
            if re.search(rf"^{param}\s*=", line, re.IGNORECASE):
                lines[i] = f"{param} = {value}\n"
                break

    # 计算 NBANDS 值，并确保其为大于 NELECT×0.6 且能被4整除的最小整数
    nbands_value = calculate_nbands(lines)
    if nbands_value is not None:
        nbands_str = str(nbands_value)
    else:
        nbands_str = "420"

    nbands_found = False
    for i, line in enumerate(lines):
        if re.search(r"^NBANDS\s*=", line, re.IGNORECASE):
            lines[i] = f"NBANDS = {nbands_str}\n"
            nbands_found = True
            break
    if not nbands_found:
        lines.append(f"NBANDS = {nbands_str}\n")
    print(f"NBANDS 参数已设置为: {nbands_str}")

    # 添加其它新参数
    for param, value in params_to_add.items():
        if not any(re.search(rf"^{param}\s*=", line, re.IGNORECASE) for line in lines):
            lines.append(f"{param} = {value}\n")

    with open(incar_path, 'w') as file:
        file.writelines(lines)
    print(f"INCAR 文件已更新: {incar_path}")

def edit_kpoints(kpoints_path):
    with open(kpoints_path, 'r') as file:
        lines = file.readlines()

    if len(lines) < 4:
        print(f"错误: KPOINTS 文件 ({kpoints_path}) 行数不足，跳过处理。")
        return

    lines[3] = "6 6 1\n"

    with open(kpoints_path, 'w') as file:
        file.writelines(lines)
    print(f"KPOINTS 文件已更新: {kpoints_path}")

def main(MAT, adsorbates):
    # 确保脚本在 Support 目录下运行
    current_dir = os.getcwd()
    if os.path.basename(current_dir) != "Support":
        print("错误: 脚本必须在 Support 目录下运行。")
        sys.exit(1)

    parent_dir = os.path.dirname(current_dir)
    for adsorbate in adsorbates:
        print(f"========== 正在处理 adsorbate: {adsorbate} ==========")
        target_dir = os.path.join(parent_dir, adsorbate, "4-dos", MAT)
        if not os.path.exists(target_dir):
            print(f"警告: 未找到目录 ({target_dir})，跳过处理。")
            continue

        incar_path = os.path.join(target_dir, "INCAR")
        if os.path.exists(incar_path):
            backup_file(incar_path)
            edit_incar(incar_path)
        else:
            print(f"警告: 未找到 INCAR 文件 ({incar_path})，跳过处理。")

        kpoints_path = os.path.join(target_dir, "KPOINTS")
        if os.path.exists(kpoints_path):
            backup_file(kpoints_path)
            edit_kpoints(kpoints_path)
        else:
            print(f"警告: 未找到 KPOINTS 文件 ({kpoints_path})，跳过处理。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修改 INCAR 和 KPOINTS 文件并备份（支持多个 adsorbate）")
    parser.add_argument('MAT', type=str, help="MAT 目录名称（4-dos/MAT）")
    parser.add_argument('adsorbate', nargs='+', help="一个或多个 adsorbate 目录名称")
    args = parser.parse_args()
    main(args.MAT, args.adsorbate)
