#!/bin/sh
dir="$1"
if [ -d "$dir" ]; then
cd "$dir"
name=$(basename "$dir")
sbatch --job-name="$name" gam-vasp.slurm
cd -
else
echo "No such files: $dir"
fi

