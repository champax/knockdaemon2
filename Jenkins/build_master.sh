#!/bin/bash

echo "=========================="
echo "build_master.sh called "
echo "=========================="

echo "Using current dir=`pwd`"

# EXPORT
export JOB_NAME=$1
export BUILD_NUMBER=$2
export

echo "=========================="
echo "JOB_NAME=${JOB_NAME}"
echo "BUILD_NUMBER=${BUILD_NUMBER}"
echo "=========================="

if [ ! -z "$JOB_NAME" ]
then
    if [ -f '/etc/debian_version' ]; then
        echo "=========================="
        echo "DEBIAN : Firing ${JOB_NAME}, calling build_client_debian.sh now (via exports)"
        echo "=========================="
        ./jenkins/build_client_debian.sh
    else
        echo "=========================="
        echo "FATAL, UNKNOWN DISTRO, Exiting in error (2)"
        echo "=========================="
        exit 2
    fi
else
    echo "=========================="
    echo "FATAL, NO JOB_NAME, Exiting in error (1)"
    echo "=========================="
    exit 1
fi
