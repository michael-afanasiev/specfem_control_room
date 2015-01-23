#!/usr/bin/env python

import os
import dataModule
import argparse

from obspy.fdsn import Client

def getArgs ():

  '''
  Parse the command line arguments/
  '''

  parser = argparse.ArgumentParser (description='Downloads stationXML metadata for a list of stations.')

  parser.add_argument (
      '--station_list', type=str, help='File which contains a list of stations',
      required=True, metavar='station list', dest='station_list')

  parser.add_argument (
      '--destination', type=str, help='Write directory for xml files',
      required=True, metavar='write dir')

  return parser.parse_args ()

args = getArgs ()
writeDir = os.path.join (args.destination)

client = Client ('IRIS')

stations, networks = dataModule.getStations (args.station_list, format='nospace')

for i, (station, network) in enumerate (zip (stations, networks)):
  
  print "Downloading: " + station + " " + network + ". File " + str (i+1) + " of " + str (len (stations)) + "." 
  stationXmlName = writeDir + 'station.' + network + '_' + station + '.xml'
  inventory      = client.get_stations (network=network, station=station, level="response")
  
  inventory.write (stationXmlName, 'StationXML')
  
