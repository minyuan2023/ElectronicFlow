import os
import shutil
import argparse
import re
import sys

def edit_incar(incar_path):
    with open(incar_path, 'r') as file:
        lines = file.readlines()

    # 更新 INCAR 文件内容：修改 IBRION、LCHARG、NSW 参数
    for i, line in enumerate(lines):
        if re.search(r"IBRION", line):
            lines[i] = re.sub(r"IBRION\s*=\s*\S+", "IBRION = -1", line)
        elif re.search(r"LCHARG", line):
            lines[i] = re.sub(r"LCHARG\s*=\s*\S+", "LCHARG = .TRUE.", line)
        elif re.search(r"NSW", line):
            lines[i] = re.sub(r"NSW\s*=\s*\S+", "NSW = 2", line)

    with open(incar_path, 'w') as file:
        file.writelines(lines)
    print(f"INCAR 文件已更新: {incar_path}")

def edit_kpoints(kpoints_path):
    with open(kpoints_path, 'r') as file:
        lines = file.readlines()

    # 修改第4行为 "1 1 1"
    if len(lines) >= 4:
        lines[3] = "1 1 1\n"

    with open(kpoints_path, 'w') as file:
        file.writelines(lines)
    print(f"KPOINTS 文件已更新: {kpoints_path}")

def process_directory(mat_dir, dos_dir):
    files_to_copy = ["INCAR", "CONTCAR", "KPOINTS", "POTCAR"]
    for file_name in files_to_copy:
        src = os.path.join(mat_dir, file_name)
        if os.path.exists(src):
            # 在目标 4-dos 目录下创建 MAT 子目录
            dest_dir = os.path.join(dos_dir, os.path.basename(mat_dir))
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            dest_path = os.path.join(dest_dir, file_name)
            shutil.copy(src, dest_path)
            # 如果复制的是 CONTCAR，则重命名为 POSCAR
            if file_name == "CONTCAR":
                poscar_path = os.path.join(dest_dir, "POSCAR")
                os.rename(dest_path, poscar_path)
                print(f"已将 {dest_path} 重命名为 {poscar_path}")
        else:
            print(f"警告: {file_name} 在 {mat_dir} 中未找到")

    incar_path = os.path.join(dos_dir, os.path.basename(mat_dir), "INCAR")
    if os.path.exists(incar_path):
        edit_incar(incar_path)
    else:
        print(f"错误: 在 {os.path.join(dos_dir, os.path.basename(mat_dir))} 中未找到 INCAR 文件。")

    kpoints_path = os.path.join(dos_dir, os.path.basename(mat_dir), "KPOINTS")
    if os.path.exists(kpoints_path):
        edit_kpoints(kpoints_path)
    else:
        print(f"错误: 在 {os.path.join(dos_dir, os.path.basename(mat_dir))} 中未找到 KPOINTS 文件。")

def main(MAT, adsorbates):
    # 确保脚本在 Support 目录下运行
    current_dir = os.getcwd()
    if os.path.basename(current_dir) != "Support":
        print("错误: 脚本必须在 Support 目录下运行。")
        sys.exit(1)

    parent_dir = os.path.dirname(current_dir)
    for adsorbate in adsorbates:
        print(f"========== 正在处理 adsorbate: {adsorbate} ==========")
        mat_dir = os.path.join(parent_dir, adsorbate, MAT)
        if not os.path.exists(mat_dir):
            print(f"错误: {mat_dir} 目录未找到。")
            continue
        dos_dir = os.path.join(parent_dir, adsorbate, "4-dos")
        if not os.path.exists(dos_dir):
            os.makedirs(dos_dir)
        process_directory(mat_dir, dos_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="复制文件并修改 INCAR 参数（支持多个 adsorbate）")
    parser.add_argument('MAT', type=str, help="MAT 目录名称")
    parser.add_argument('adsorbate', nargs='+', help="一个或多个 adsorbate 目录名称")
    args = parser.parse_args()
    main(args.MAT, args.adsorbate)
