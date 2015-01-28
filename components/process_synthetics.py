#!/usr/bin/env python

import math
import argparse
import os
import obspy
import numpy as np

from classes.seismogram import SyntheticSeismogram
from classes.cmt_solution import CMTSolution
from multiprocessing import Pool, cpu_count


def run_processing_script(file):
    
    print 'Processing: ' + os.path.basename(file)
    seismogram = SyntheticSeismogram(file)
    cmtsolution = CMTSolution(args.cmt_file)
    seismogram.fill_to_start_time(cmtsolution.time_shift)
    seismogram.convolve_stf(cmtsolution)
    seismogram.convert_to_velocity()
    seismogram.reset_length()
    seismogram.filter(args.min_p, args.max_p)
    seismogram.write_specfem_ascii(file + '.convolved.filtered')
    seismogram.write_sac(file)
    
# ---
parser = argparse.ArgumentParser(description='Performs post processing on a '
                                             'directory of .ascii seismograms')
parser.add_argument('-f', type=str, help='Path to ascii seismogram file, or '
                    'directory of files.',
                    dest='seismo_file', required=True)
parser.add_argument('-cmt', type=str, help='Path to cmt solution',
                    dest='cmt_file', required=True)
parser.add_argument(
    '--min_p', type=float, help='Minimum period', required=True)
parser.add_argument(
    '--max_p', type=float, help='Maximum period', required=True)
parser.add_argument('--whole_directory', help='Loop through all seismograms '
                    'in a directory, rather than just a single one.',
                    action='store_true')
args = parser.parse_args()
# ---

# Fix any paths.
args.seismo_file = os.path.abspath(args.seismo_file)
args.cmt_file = os.path.abspath(args.cmt_file)

target_files = []
if args.whole_directory:
    for file in os.listdir(args.seismo_file):
        if file.endswith('.ascii'):
            target_files.append(os.path.join(args.seismo_file, file))
else:
    target_files.append(args.seismo_file)

print "Running on " + str(cpu_count()) + " cores."
if __name__ == '__main__':
    
    pool = Pool(processes=cpu_count()/2)
    pool.map(run_processing_script, target_files)