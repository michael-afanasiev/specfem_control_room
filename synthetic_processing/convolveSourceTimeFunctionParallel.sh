#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="convolve synthetics"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=./logs/convolve.%A.%a.o
#SBATCH --error=./logs/convolve.%A.%a.e

export MV2_ENABLE_AFFINITY=0
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=8

if [ "$1" == '' ]; then
  echo "Usage: ./convolveSyntheticsParallel [master_forward_dir]"
  exit
fi

iterationDir=$1

shopt -s nullglob

# Get event names.
array=($iterationDir/*)

# Parse name from path.
myEvent=${array[$SLURM_ARRAY_TASK_ID]}
seismo_dir=$(readlink -m $myEvent/OUTPUT_FILES/)
cmtSolution=$(readlink -m $myEvent/DATA/CMTSOLUTION)

echo "Convolving files in: $(readlink -m $myEvent)"
echo "Using CMTSOLUTION: $cmtSolution"
aprun -n 1 -N 1 -d 8 ./convolveSourceTimeFunction.py --seismogram_dir $seismo_dir --half_duration 3.805 --cmt_solution_file $cmtSolution
