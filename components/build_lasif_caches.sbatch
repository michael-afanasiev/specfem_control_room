#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="cache"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --output=./logs/cache.o
#SBATCH --error=./logs/cache.e

# Report what's what.
echo "Submitted command: build_lasif_cachces.sbatch $1 $2"

# Change to the lasif directory.
lasif_base_dir=$1
lasif_scratch_dir=$2

# Sync lasif base with lasif scratch.
rsync -av $lasif_base_dir $lasif_scratch_dir

# Chance to lasif scratch
cd $lasif_scratch_dir

# Run the cache builder.
aprun -n 1 -N 1 lasif build_all_caches

# Sync back.
rsync -av $lasif_scratch_dir $lasif_base_dir