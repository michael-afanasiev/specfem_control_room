#!/usr/bin/env python

import math
import obspy
import argparse

def distribute_adjoint_sources():
    
    print 'Distributing.'
    
parser = argparse.ArgumentParser(description='Formats and distributes the '
                                             'adjoint source for SPECFEM')
parser.add_argument('--iteration_name', type=str, help='Iteration name',
                    required=True)
