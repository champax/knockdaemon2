#!/bin/bash -e

# Intended for local test
# Bash : Go to this file directory and execute it
echo "*** RESET"
mkdir -p /tmp/ktemp/
rm -rf /tmp/ktemp/*
mkdir -p /tmp/ktemp/.virtualenvs
rm -rf /tmp/ktemp/.virtualenvs

mkdir -p /tmp/ktemp/python3-knockdaemon2/label/debian10
mkdir -p /tmp/ktemp/.virtualenvs

echo "*** LS"
ls -lRa /tmp/ktemp/*

echo "*** CP"
cp -R ../* /tmp/ktemp/python3-knockdaemon2/label/debian10

echo "*** EXPORT"
export WORKSPACE="/tmp/ktemp/python3-knockdaemon2/label/debian10"
export BUILD_NUMBER="99"
export V_ENV_ROOT="/tmp/ktemp/.virtualenvs"
export Branch="local"

echo "*** CD"
cd /tmp/ktemp/python3-knockdaemon2/label/debian10
pwd

echo "*** INVOKE"
./Jenkins/build_client_debian.sh


