#!/bin/bash

breqFastFolder=./MISC/breqFastRequests

for file in $breqFastFolder/*.bqFast; do
  echo "Sending: $file to breq_fast@iris.washington.edu"
  cat $file | mail -s 'bqFast Request.' breq_fast@iris.washington.edu
  sleep 5
done
