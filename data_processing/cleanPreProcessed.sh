#!/bin/bash 

for dir in ./DATA/*; do
  rm -rf $dir/preprocessed*
done
