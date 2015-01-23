#!/usr/bin/env python

import os
import sys
import obspy
import argparse
import subprocess

import numpy as np

import dataModule as dm

#----- Command line arguments.
parser = argparse.ArgumentParser (description='Processes ASCII specfem seismograms.')

parser.add_argument (
  '--convolve', help='This program will not try and convolve the \
  synthetic seismograms with a source time function.', default=False, 
  action="store_true")
  
parser.add_argument (
  '--convolve_binary', type=str, help='Path to the specfem convolve script/binary\
  cshell script.', metavar='sourcetimeFunction dir'
)

parser.add_argument (
  '--seismogram_dir', type=str, help='Directory of (convolved) specfem seismogram', 
  required=True, metavar='Seismo dir')
  
parser.add_argument (
  '--max_period', type=float, help='Long period corner', required=True, metavar='LP corner')
  
parser.add_argument (
  '--min_period', type=float, help='Short period corner', required=True, metavar='SP corner')
  
parser.add_argument (
  '--write_dir', type=str, help='Write directory for processed synthetic seismograms', 
  required=True, metavar='Write dir'
)

args = parser.parse_args ()
#----- End command line arguments.

# Check for parser consistency.
if args.convolve and args.convolve_binary == None:
  print dm.colours.FAIL + "You've indicated you want to convolve, but haven't specified\
  the xconvolve_source_time_function binary. Exiting." + dm.colours.ENDC
  sys.exit ()
  
if args.convolve:
  print "Convolving seismograms."
  xconvolve_bin = os.path.join (args.seismogram_dir, '../', 'bin', 'xconvolve_source_timefunction')
  proc = subprocess.Popen ([args.convolve_binary, args.seismogram_dir, xconvolve_bin], 
  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = proc.communicate ()
  retcode = proc.wait ()
  
# For all seismograms in the seismogram directory.
for dirname, dirnames, filenames in os.walk (args.seismogram_dir):  
  for filename in filenames:
      
    # Skip those files which are not convolved.
    if not 'convolved' in filename:
      continue

    # Read ascii file, and calculate dt.
    print 'Processing: ' + filename
    filename = os.path.join (dirname, filename)
    temp     = np.loadtxt(filename, dtype=np.float64)
    t, data  = temp[:, 0], temp[:, 1]
    dt       = abs (t[1] - t[0])

    # Kick out samples before time 0. Don't do this. start of specfem simulation corresponds to
    # rise time.
#    tNew    = []
#    dataNew = []
#    for pair in zip (t, data):
#      if pair[0] >= 0:
#        tNew.append (pair[0])
#        dataNew.append (pair[1])
        
#    t    = tNew
#    data = dataNew

    # Initialze obspy trace.
    tr             = obspy.Trace(data=temp[:, 1])
    tr.stats.delta = dt
    tr.stats.station, tr.stats.network, tr.stats.channel = \
        os.path.basename(filename).split(".")[:3]

    # Name channels correctly.
    if   'MXN' in tr.stats.channel:
      tr.stats.channel = 'X'
    elif 'MXE' in tr.stats.channel:
      tr.stats.channel = 'Y'
    elif 'MXZ' in tr.stats.channel:
      tr.stats.channel = 'Z'

    # # Bandpass filter.
    tr.filter ('lowpass',  freq=(1/args.min_period), corners=5, zerophase=True)
    tr.filter ('highpass', freq=(1/args.max_period), corners=2, zerophase=True)
    
    # Write to sac file.    
    if not (os.path.isdir (args.write_dir)):
      os.mkdir (args.write_dir)
    sacFileName = os.path.join (
      args.write_dir, tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.channel + '.mseed')    
    tr.write (sacFileName, format='MSEED')
