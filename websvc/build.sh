#!/bin/bash

# trap errors and print failure info
trap ': "*** BUILD FAILED ***" $BASH_SOURCE:$LINENO: error: "$BASH_COMMAND" returned $?' ERR

# print commands executed, exit on errors
set -eExuo pipefail

# print version of bash we're using
echo "BASH VERSION: $BASH_VERSION"

# set the expected pip version
PIP_VERSION=9.0.1

rm -rf ./build/
mkdir -p build

# create virtual environment
virtualenv -p `which python3` ./build/.env

cd ./build/.env
set +u
source ./bin/activate
set -u

# upgrade pip
pip install --upgrade pip==${PIP_VERSION} 

# emit python and pip versions
python --version
pip --version

# install python dependencies
pip install -r ../../requirements.txt --no-cache-dir

cd ../../

# basic syntax checking
python -m compileall *.py

# more involved pylint checking
# TODO reenable this
#pylint *.py

# run unit tests
python -m unittest tests.py

# success
: "*** BUILD SUCCESSFUL ***"
