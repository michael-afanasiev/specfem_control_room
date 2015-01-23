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

cd ./DATA/$myEvent/preprocessed_hp_0.00833_lp_0.01667_npts_153069_dt_0.142500/
tar -xvf preprocessedData.tar
rm -f preprocessedData.tar

cd ../../../SYNTHETICS/$myEvent/ITERATION_$iterationName
tar -xvf synthetics.tar
rm -f synthetics.tar

aprun -B lasif select_windows $iterationName $myEvent

tar -cvf synthetics.tar *.mseed
rm -f *.mseed

cd ../../../DATA/$myEvent/preprocessed_hp_0.00833_lp_0.01667_npts_153069_dt_0.142500/
tar -cvf preprocessedData.tar *.mseed
rm -f *.mseed
