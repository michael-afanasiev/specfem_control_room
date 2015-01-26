#!/usr/bin/env python

import os
import sys
import math
import argparse

import numpy as np

from itertools import repeat
from multiprocessing import Pool, cpu_count

parser = argparse.ArgumentParser (description="Convolves with a gaussian "
    "sourcetime function.")

parser.add_argument (
  '--half_duration', help='Half duration of the gaussian', required=True, metavar='half duration',
  type=float)

parser.add_argument (
  '--seismogram_dir', type=str, help='Directory of specfem seismograms', 
  required=True, metavar='Seismo dir')

parser.add_argument (
  '--cmt_solution_file', type=str, help='Location of CMT solution file (for time shift information)',
  required=True, metavar='Cmtsolution')

args = parser.parse_args ()

# Set up constants
SOURCE_DECAY_MIMIC_TRIANGLE = 1.6280
alpha                       = SOURCE_DECAY_MIMIC_TRIANGLE / args.half_duration

def getTimeShift ():
  
  file = open (args.cmt_solution_file, 'r')
  for line in file:
    if 'time shift' in line:
      timeShift = float (line.split ()[2])
      
  return timeShift

def convolve ((fileName, halfDuration, timeShift)):
  
  '''
  Convolves an ascii file output from specfem with a gaussian of a specified half-duration. Outputs
  this convolved seismogram with .convolved at the end of it.
  '''
  
  print 'Convolving: ' + fileName 
  temp     = np.loadtxt (fileName)
  t, data  = temp[:, 0], temp[:, 1]
  dt       = t[1] - t[0]
  origLen  = len (t)
  
  # Fill into pde time.
  tEarly = t[0]
  newTimeArr = []
  newSiesArr = []
  while abs (tEarly) < timeShift:
    
    tEarly = tEarly - dt
    newTimeArr.append (tEarly)
    newSiesArr.append (0.)
    
  newTimeArr = newTimeArr[::-1]
  t          = np.insert (t, 0, newTimeArr)
  data       = np.insert (data, 0, newSiesArr)
  
  # Get number of convolvable samples.
  nSamples = len (data)  
  nJ       = int (math.ceil (1.5 * halfDuration / dt))  
  dataFilt = np.zeros_like (data)
  dataVel  = np.zeros_like (data)
  
  
  # Finite difference -- switch to velocity.
  for i in range (1, nSamples-1):
    dataVel[i] = (data[i+1] - data[i-1]) / (2 * dt)

  dataVel[0]          = (data[1] - data[0]) / dt
  dataVel[nSamples-1] = (data[nSamples-1] - data[nSamples-2]) / dt

  # Copy back to data array.
  data = dataVel

  # Move along time Axis
  for i, sample in enumerate (np.nditer(data)):    
    for j in range (-nJ, nJ+1):      
      
      # Set up exponent value.
      tau      = j * dt
      exponent = alpha*alpha * tau*tau
      
      # If we're quite small, don't bother with this.
      if (exponent < 50):
        source = alpha * math.exp (-exponent) / math.sqrt (math.pi)
      else:
        source = 0
        
      # Pad with zeros (zero-phase).
      if i+j < 0 or i+j > nSamples-1:
        filterMe = 0
      else:
        filterMe = data[i+j]
      
      # Save to new array.
      dataFilt[i] = dataFilt[i] + filterMe * source * dt

  t = t[:origLen]
  dataFilt = dataFilt[:origLen]
  np.savetxt (fileName + '.convolved', np.c_[t, dataFilt], newline='\n', fmt='%10e')

##### BEGIN SCRIPT #####

timeShift = getTimeShift ()

# Loop through seismograms
convolveFiles = []
for file in os.listdir (args.seismogram_dir):
  
  # Skip files that aren't seismograms.
  if not file.endswith ('sem.ascii'):
    continue
    
  fileName = os.path.join (args.seismogram_dir, file)
  convolveFiles.append (fileName)
  
if __name__ == '__main__':
  
  pool = Pool (processes=cpu_count ()/2)
  pool.map (convolve, zip (convolveFiles, repeat (args.half_duration), repeat (timeShift)))
