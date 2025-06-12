#!/bin/sh
dir="$1"
if [ -d "$dir" ]; then
cd "$dir"
sbatch std-vasp.slurm
cd -
else
echo "No such files: $dir"
fi

