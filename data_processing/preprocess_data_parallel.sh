#!/bin/bash -l

#SBATCH --account=ch1
#SBATCH --job-name="preprocessing"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=./logs/preprocessing.%A.%a.o
#SBATCH --error=./logs/preprocessing.%A.%a.e

export MV2_ENABLE_AFFINITY=0
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=8

if [ "$3" == '' ]; then
  echo "Usage: ./preprocess_data_parallel [lasif_scratch_dir] [lasif_base_dir] [iteration_name]"
  exit
fi

lasif_scratch_dir=$1
lasif_base_dir=$2
iteration_name=$3
eventsDir=$lasif_scratch_dir/EVENTS
dataDir=$lasif_scratch_dir/DATA
shopt -s nullglob

# Get event names.
array=($eventsDir/*)

# Parse name from path.
myEvent=${array[$SLURM_ARRAY_TASK_ID]}
myEvent=${myEvent%.xml}
myEvent=${myEvent##*/}

echo "PREPROCESSING: $myEvent\n\n"

# # Move to the raw data directory, extract the data, and kick out the rawData.tar.
cd $dataDir/$myEvent/raw
tar -xvf data.tar
rm data.tar

# Run the preprocessing.
aprun -n 1 -N 1 -d 8 lasif preprocess_data $iteration_name $myEvent --read_only_caches

# # Re-tar the raw files.
tar -cvf data.tar
rm -f *.mseed

# Change back to event data directory.
cd ../

# Get most recently created directory (will be preprocessed one)
for f in ./preprocessed*; do
  if [ -d "$f" ]; then
    cd $f
    if [ ! -e ./data.tar ]; then
      tar -cvf ./data.tar *.mseed
      rm -f *.mseed
      cd ../
      rsync -av $f $lasif_base_dir/DATA/$myEvent/
    fi
  fi
done
