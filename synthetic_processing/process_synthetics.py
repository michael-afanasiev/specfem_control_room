#!/usr/bin/env python

import math
import argparse
import os
import obspy
import numpy as np

from multiprocessing import Pool, cpu_count

class SyntheticSeismogram(object):

    def __init__(self, file_name):
        """
        Reads in an ascii seismogram, in the specfem3d_globe format. Returns a
        synthetic seismogram object.

        :file_name: File name of ascii specfem3d_globe seismogram.
        """

        temp = np.loadtxt(file_name)
        self.t, self.data = temp[:, 0], temp[:, 1]
        self.dt = self.t[1] - self.t[0]
        self.orig_len = len(self.t)
        self.fname = file_name

        self.tr = obspy.Trace(data=self.data)
        self.tr.stats.delta = self.dt
        self.tr.stats.station, self.tr.stats.network, self.tr.stats.channel = \
            os.path.basename(self.fname).split('.')[:3]

        if 'MXN' in self.tr.stats.channel:
            self.tr.stats.channel = 'X'
        elif 'MXE' in self.tr.stats.channel:
            self.tr.stats.channel = 'Y'
        elif 'MXZ' in self.tr.stats.channel:
            self.tr.stats.channel = 'Z'

    def fill_to_start_time(self, time_shift):
        """
        Takes the time shift information and pads the beginning of the
        seismograms with zeros to extend them to the actual start time. Returns
        the orignal arrays, extended.

        :time_shift: Time shift parameter (usually gathered from CMT solution)
        """

        t_early = self.t[0]
        new_time_arr = []
        new_wave_arr = []
        while abs(t_early) < time_shift:
            t_early = t_early - self.dt
            new_time_arr.append(t_early)
            new_wave_arr.append(0.)

        new_time_arr = new_time_arr[::-1]
        self.t = np.insert(self.t, 0, new_time_arr)
        self.data = np.insert(self.data, 0, new_wave_arr)
        self.length = len(self.data)

    def write_specfem_ascii(self, file_name):
        """
        Writes a seismogram object into the specfem3d_globe format.

        :file_name: Output file name.
        """

        np.savetxt(file_name, np.c_[self.t, self.data], newline='\n',
                   fmt='%10e')

    def convert_to_velocity(self):
        """
        Uses a centered finite-difference approximation to convert a
        displacement seismogram to a velocity seismogram.
        """

        self.data = np.gradient(self.data, self.dt)

    def convolve_stf(self, cmt_solution):
        """
        Convolves with a gaussian source time function, with a given
        half_duration. Does this in place. Takes a cmtsolution object as a
        parameter.

        :cmt_solution: Cmt_solution object passed.
        """

        n_convolve = int(math.ceil(1.5 * cmt_solution.half_duration / self.dt))
        g_x = np.zeros(2 * n_convolve + 1)

        for i, j in enumerate(range(-n_convolve, n_convolve + 1)):
            tau = j * self.dt
            exponent = cmt_solution.alpha * cmt_solution.alpha * tau * tau
            source = cmt_solution.alpha * math.exp(-exponent) / \
                math.sqrt(math.pi)

            g_x[i] = source * self.dt

        self.data = np.convolve(self.data, g_x, 'same')

    def reset_length(self):
        """
        Resets the length of the seismogram to the original length output from
        specfem. It does this by cutting off the last couple samples from the
        seismogram.
        """

        self.t = self.t[:self.orig_len]
        self.data = self.data[:self.orig_len]

    def filter(self, min_period, max_period):
        """
        Performs a bandpass filtering and renaming of station and channels to
        fit into LASIF's world.
        """

        self.tr.data = self.data

        self.tr.filter('lowpass', freq=(1 / min_period), corners=5,
                       zerophase=True)
        self.tr.filter('highpass', freq=(1 / max_period), corners=2,
                       zerophase=True)

        self.data = self.tr.data
        
    def write_sac(self, file):
        """
        Write a sac file.
        
        :file: File name.
        """
        
        base_path = os.path.dirname(file)
        file_name = self.tr.stats.network + '.' + self.tr.stats.station + '.' +\
            self.tr.stats.channel + '.mseed'
        write_path = os.path.join(base_path, file_name)
        self.tr.write(write_path, format='MSEED')

class CMTSolution(object):

    def __init__(self, cmt_solution_file):
        """
        Searches a cmt file for time shift information. Returns a CMT object.

        :cmt_solution_file: Location of CMT solution file.
        """

        file = open(cmt_solution_file, 'r')
        for line in file:
            if 'time shift' in line:
                self.time_shift = float(line.split()[2])

        self.half_duration = 3.805
        self.source_decay_mimic_triangle = 1.6280
        self.alpha = self.source_decay_mimic_triangle / self.half_duration
        
        
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