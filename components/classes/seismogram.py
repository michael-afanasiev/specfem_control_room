#!/usr/bin/env python

import os
import math
import obspy
import numpy as np

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
