#!/usr/bin/env python

import dataModule

import os
import csv
import argparse
import datetime

from string import Template

def getArgs ():
  
  '''
  Parse the command line arguments.
  '''

  parser = argparse.ArgumentParser (description='Generates a BreqFast request.')
  
  parser.add_argument (
    '--event_name', type=str, help='Name of the event', required=True, metavar='event_name')

  parser.add_argument (
    "--station_list", type=str, help='File which contains list of stations',
    required=True, metavar='Station list', dest="station_list")

  parser.add_argument (
    '--start_time', type=str, help='Start time of request', nargs=7, required=True,
    metavar=('YYYY', 'MM', 'DD', 'HH', 'MM', 'SS', 'TTTT'))  

  parser.add_argument (
    '--recording_time', type=float, help='Recording time (in hours)', required=True,
    metavar=('hours'))

  return parser.parse_args ()
  
'''
Generate breakfast request.
'''

if not os.path.exists ('./MISC'):
  os.makedirs ('./MISC')

if not os.path.exists ('./MISC/breqFastRequests'):
  os.makedirs ('./MISC/breqFastRequests')

args = getArgs ()

templateFile = open ('./dataHelpers/breqFastTemplate.txt', 'r')
header       = Template (templateFile.read ())
templateFile.close ()

newHeaderArgs = {'LABEL':args.event_name}
newHeader     = header.substitute (newHeaderArgs)

stations, networks = dataModule.getStations (args.station_list)

sYear   = int (args.start_time[0])
sMonth  = int (args.start_time[1])
sDay    = int (args.start_time[2])
sHour   = int (args.start_time[3])
sMinute = int (args.start_time[4])
sSecond = int (args.start_time[5])
sMicro  = int (args.start_time[6])

startTime = datetime.datetime (sYear, sMonth, sDay, sHour, sMinute, sSecond, sMicro)
delta     = datetime.timedelta (hours=args.recording_time)
endTime   = startTime + delta

end_time = []
end_time.append (str (endTime.year))
end_time.append (str (endTime.month).zfill(2))
end_time.append (str (endTime.day).zfill(2))
end_time.append (str (endTime.hour).zfill(2))
end_time.append (str (endTime.minute).zfill(2))
end_time.append (str (endTime.second).zfill(2))
end_time.append (str (endTime.microsecond).zfill(2))

startMicroString = '.'.join (args.start_time[-2::])
endMicroString   = '.'.join (end_time[-2::])

del args.start_time[-2::]
del end_time[-2::]

args.start_time.append (startMicroString)
end_time.append (endMicroString)

request = open ('./MISC/breqFastRequests/' + args.event_name +'.bqFast', 'w')
request.write (newHeader)
for station in zip (stations, networks):
  request.write (' '.join (station) + ' ' + ' '.join(args.start_time) + ' ' + 
  ' ' .join(end_time) + ' 2 BH? L??' + '\n')

print "Generated BreqFast request for " + args.event_name
