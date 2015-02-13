#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="window_selecion"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --output=./logs/window.%A.%a.o
#SBATCH --error=./logs/window.%A.%a.e

export MV2_ENABLE_AFFINITY=0
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=8

if [ "$1" == "" ]; then
  echo "Usage: ./select_windows_parallel.sh [lasif_dir] [iteration_name]"
  exit
fi

lasifDir=$1
iterationName=$2

cd $lasifDir
shopt -s nullglob
array=($lasifDir/EVENTS/*)

myEvent=${array[$SLURM_ARRAY_TASK_ID]}
myEvent=${myEvent%.xml}
myEvent=${myEvent##*/}

aprun -B lasif select_windows $iterationName $myEvent --read_only_caches
