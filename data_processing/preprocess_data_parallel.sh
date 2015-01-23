#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="preprocessing"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=../OUTPUT/slurm_output/preprocessing.%A.%a.o
#SBATCH --error=../OUTPUT/slurm_output/preprocessing.%A.%a.e

export MV2_ENABLE_AFFINITY=0
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=8

if [ "$1" == '' ]; then
  echo "Usage: ./preprocess_data_parallel [iteration_name]"
  exit
fi

eventsDir=../EVENTS/
iterationName=$1
dataDir=../DATA/

shopt -s nullglob

# Get event names.
array=($eventsDir/*)

# Parse name from path.
myEvent=${array[$SLURM_ARRAY_TASK_ID]}
myEvent=${myEvent%.xml}
myEvent=${myEvent##*/}

echo "PREPROCESSING: $myEvent\n\n"

# Move to the raw data directory, extract the data, and kick out the rawData.tar.
cd $dataDir/$myEvent/raw
tar -xvf rawData.tar
rm -f rawData.tar

# Run the preprocessing.
aprun -n 1 -N 1 -d 8 lasif preprocess_data $iterationName $myEvent

# Re-tar the raw files.
tar -cvf rawData.tar *.mseed
rm -f *.mseed

# Change back to event data directory.
cd ../

# Get most recently created directory (will be preprocessed one)
for f in ./preprocessed*; do
  if [ -d "$f" ]; then
    cd $f
    if [ ! -e ./preprocessedData.tar ]; then
      tar -cvf preprocessedData.tar *.mseed
      rm -f *.mseed
    fi
  fi
done
