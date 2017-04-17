#!/bin/bash

set -ex 
cd ../..
bash -ex create_exes.sh $1
cd distribution/debian
bash -ex createdeb.sh $1
