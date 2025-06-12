import sys
import os
from pymatgen.io.vasp import Potcar, Poscar


def get_zvals_from_potcar(potcar_path):
    """从POTCAR文件中获取每个元素的ZVAL价电子数。"""
    if not os.path.exists(potcar_path):
        raise FileNotFoundError(f"POTCAR 文件不存在：{potcar_path}")
    potcar = Potcar.from_file(potcar_path)
    return [float(pot.keywords['ZVAL']) for pot in potcar]


def get_atom_counts_from_poscar(poscar_path):
    """从POSCAR文件获取每种元素的原子数。"""
    if not os.path.exists(poscar_path):
        raise FileNotFoundError(f"POSCAR 文件不存在：{poscar_path}")
    structure = Poscar.from_file(poscar_path).structure
    return [structure.composition[el] for el in structure.composition.elements]


def calculate_nelect(zvals, atom_counts, net_charge):
    """根据ZVAL、原子数和净电荷计算NELECT值。"""
    nelect = sum(zval * count for zval, count in zip(zvals, atom_counts)) - net_charge
    return int(nelect)


def update_nelect_in_incar(incar_path, nelect):
    """在INCAR文件中更新或添加NELECT参数。"""
    if not os.path.exists(incar_path):
        raise FileNotFoundError(f"INCAR 文件不存在：{incar_path}")
    with open(incar_path, 'r') as file:
        lines = file.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith('NELECT'):
            lines[i] = f'  NELECT = {nelect}\n'
            updated = True
            break

    if not updated:
        lines.append(f'  NELECT = {nelect}\n')

    with open(incar_path, 'w') as file:
        file.writelines(lines)


def main():
    if len(sys.argv) < 4:
        print("Usage: python NELECT.py MAT net_charge adsorbate1 [adsorbate2 ...]")
        sys.exit(1)

    # 直接从命令行传入 MAT, net_charge 和 adsorbates
    MAT = sys.argv[1]
    net_charge = int(sys.argv[2])
    adsorbates = sys.argv[3:]

    base_dir = os.path.abspath(os.path.dirname(__file__))  # 脚本所在目录

    for adsorbate in adsorbates:
        print(f"Processing adsorbate: {adsorbate}")

        # 构造POTCAR、POSCAR和INCAR的路径
        potcar_path = os.path.join(base_dir, adsorbate, MAT, 'POTCAR')
        poscar_path = os.path.join(base_dir, adsorbate, MAT, 'POSCAR')
        incar_path = os.path.join(base_dir, adsorbate, MAT, 'INCAR')

        # 获取POTCAR中的ZVAL和POSCAR中的原子数
        zvals = get_zvals_from_potcar(potcar_path)
        atom_counts = get_atom_counts_from_poscar(poscar_path)

        # 计算NELECT
        nelect = calculate_nelect(zvals, atom_counts, net_charge)

        # 更新INCAR文件
        update_nelect_in_incar(incar_path, nelect)
        print(f"NELECT = {nelect} has been written to {incar_path}")


if __name__ == "__main__":
    main()
