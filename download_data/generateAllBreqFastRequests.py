#!/usr/bin/env python

import re
import os
import argparse
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser (description='Generates a driver file to help the creation of a large number of breqFast requests')

parser.add_argument (
    "--recording_time", type=str, help="Recording time desired", required=True, metavar='recording time')

parser.add_argument (
    "--station_list", type=str, help="name of file containing the station list", 
    required=True, metavar='station file name')

args = parser.parse_args ()


eventNames = []
eventTimes = []
quakeMLString = '{http://quakeml.org/xmlns/bed/1.2}'
for root, _, files in os.walk ('./EVENTS'):
  for file in files:

    print 'Parsing: ' + file
    eventNames.append (os.path.splitext (file)[0])

    fullPath = os.path.join (root, file)
    
    tree     = ET.parse (fullPath)
    treeRoot = tree.getroot ()
    for elem in tree.iter ():
      if elem.tag == (quakeMLString + 'origin') and 'ref' in elem.attrib['publicID']:
        for child in elem:
          if child.tag == quakeMLString + 'time':
            for time in child:
              eventTimes.append (time.text)

eventString = []
for event in eventNames:
  if "'" in event:
    cleanString = event.replace ("'", "")
  else:
    cleanString = event

  eventString.append (cleanString)

timeString = []
for time in eventTimes:

  cleanTime = re.split (r':|-|T|\.', time)
  cleanTime[-1] = cleanTime[-1][:-5]
 
  timeString.append (' '.join (cleanTime))

f = open ('breqFastDriver.sh', 'w')
f.write ('#/bin/bash \n')
for event, time in zip (eventString, timeString):
  f.write (
      './dataHelpers/generateBreqFastRequest.py --event_name ' + event + ' ' + 
      '--station_list ' + args.station_list + ' ' +
      '--start_time ' + time + ' ' +
      '--recording_time ' + args.recording_time + '\n')

f.close ()

print "\nNow run the command 'sh ./breqFastDriver.sh' to batch generate your breqFast requests.'"
