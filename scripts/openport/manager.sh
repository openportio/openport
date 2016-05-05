#!/bin/bash

SOURCE="$0"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve i$
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

cd $DIR

env/bin/python manager/openportmanager.py &
trap "kill $!" 2 3 15
wait
