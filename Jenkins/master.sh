#!/bin/bash

export JOB_NAME=$1
export BUILD_NUMBER=$2
export JD=$3


export
# Test if jenkins project is knockdaemon2Master
echo ==============
echo  Building ${JOB_NAME}
echo ==============

if [ ! -z "$JOB_NAME" ]
then
    # JOB_NAME exist
    if [ "$JOB_NAME" == "knockdaemon2Master" ]
    then
        # build all
        echo Build client and server
	    export BUILDMODE=SERVER
        ./Jenkins/server_build.sh
        exit 0
    fi
    if [[ ${JOB_NAME} == "knockdaemon2" ]]
    then
        # build client only
        set -x
        echo Build client only
	      export BUILDMODE=CLIENT
        ./Jenkins/client_build.sh
        exit 0
    fi
    echo "JOB_NAME UNKNOW"
    exit 1
else
echo "JOB_NAME must be set"
exit 1
fi
