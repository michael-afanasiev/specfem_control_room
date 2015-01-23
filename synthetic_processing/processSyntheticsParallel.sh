#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="process synthetics"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --output=./logs/process.%A.%a.o
#SBATCH --error=./logs/process.%A.%a.e

export MV2_ENABLE_AFFINITY=0
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=8

if [ "$2" == '' ]; then
  echo "Usage: ./processSyntheticsParallel [master_forward_dir] [lasif_base_dir]"
  exit
fi

iterationDir=$1
lasifBaseDir=$2

shopt -s nullglob

# Get event names.
array=($iterationDir/*)

echo $myEventRaw

# Parse name from path.
myEvent=${array[$SLURM_ARRAY_TASK_ID]}
seismo_dir=$(readlink -m $myEvent/OUTPUT_FILES/)

# Get name of lasif synthetic dir
iterationName=$(basename $iterationDir)
myEventRaw=${myEvent##*/}
lasifSyntheticDir=$(readlink -m $lasifBaseDir/SYNTHETICS/$myEventRaw/ITERATION_$iterationName)

aprun -n 1 -N 1 ./processSynthetics.py --seismogram_dir $seismo_dir --write_dir $seismo_dir --min_period 60 --max_period 120

# Change to directory and tar files.
cd $seismo_dir
tar -cvf ./synthetics.tar *.mseed
mkdir -p $lasifSyntheticDir
mv $seismo_dir/synthetics.tar $lasifSyntheticDir
