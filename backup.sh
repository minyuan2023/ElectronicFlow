#!/bin/sh
dir="$1"
if [ -d "$dir" ]; then
cd "$dir"
# 定义一个函数，用于获取当前最大的备份编号
get_max_backup_number() {
    base_name=$1   # 文件基名，如 CONTCAR 或 POSCAR
    prefix=$2      # 前缀，如 old

    # 使用 ls 和 grep 筛选出符合命名格式的文件
    # 提取编号部分，并找出最大的编号
    max_num=$(ls ${base_name}-${prefix}* 2>/dev/null | \
              grep -E "${base_name}-${prefix}[0-9]+" | \
              sed -E "s/${base_name}-${prefix}//" | \
              sort -n | \
              tail -1)

    # 如果没有找到任何备份文件，返回0
    if [ -z "$max_num" ]; then
        echo 0
    else
        echo "$max_num"
    fi
}

backup_file() {
    file=$1
    base_name=$(basename "$file")
    prefix="old"

    # 先检查文件是否存在且不为空
    if [ ! -e "$file" ]; then
        echo "警告: 文件 $file 不存在，跳过备份。"
        return
    elif [ ! -s "$file" ]; then
        echo "警告: 文件 $file 为空，跳过备份。"
        return
    fi

    # 获取最大备份编号
    max_n=$(get_max_backup_number "$base_name" "$prefix")
    new_n=$((max_n + 1))
    backup_name="${base_name}-${prefix}${new_n}"

    # 执行备份
    cp -r "$file" "$backup_name"

    # 检查备份是否成功
    if [ $? -eq 0 ]; then
        echo "备份文件已保存为 $backup_name"
    else
        echo "错误: 备份 $file 失败。"
        exit 1
    fi
}

# 备份 POSCAR 文件，先检查文件是否存在且不为空
backup_file "POSCAR"

# 备份 CONTCAR 文件，先检查文件是否存在且不为空
backup_file "CONTCAR"

backup_file "OUTCAR"
# 检查 CONTCAR 是否存在且不为空，然后将其复制为 POSCAR
if [ ! -e "CONTCAR" ]; then
    echo "错误: CONTCAR 文件不存在，无法复制为 POSCAR。"
    echo "POSCAR 文件保持不变"
elif [ ! -s "CONTCAR" ]; then
    echo "错误: CONTCAR 文件为空，无法复制为 POSCAR。"
    echo "POSCAR 文件保持不变"
else
    # CONTCAR 文件存在且不为空，可以复制
    if cp -r CONTCAR POSCAR; then
        echo "CONTCAR 已成功复制为 POSCAR"
    else
        echo "错误: 将 CONTCAR 复制为 POSCAR 失败。"
        exit 1
    fi
fi



cd -
else
echo "No such files: $dir"
fi

