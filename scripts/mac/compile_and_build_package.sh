#!/bin/sh

cd ../client
bash -ex ./create_exes.sh
cd ../mac
bash -ex ./build.sh
