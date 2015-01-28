#!/usr/bin/env python

import os
import math
import obspy
import numpy as np

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
