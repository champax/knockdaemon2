#!/bin/bash

# Exit on error
set -e

# Export everything needed
export WORKON_HOME=/opt/knock/.env
export KNOCK_HOME=/opt/knock/knockdaemon2
export PIP_VIRTUALENV_BASE=${WORKON_HOME}
export PIP_RESPECT_VIRTUALENV=true

# Packages
aptitude update
aptitude install -y virtualenvwrapper build-essential python-dev file smartmontools ipmitool dmidecode sudo

# make home dir
mkdir -p ${WORKON_HOME}

# Source the virtual env stuff (debian specific)
source /etc/bash_completion.d/virtualenvwrapper

# Errors off
set +e

# Remove the virtual env
rmvirtualenv knockdaemon2 2>/dev/null

# Make the virtual env
mkvirtualenv knockdaemon2

# Errors on
set -e

# Our dir
CONTRIB_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# install
cd ${CONTRIB_DIR}/..
python ${CONTRIB_DIR}/../setup.py install

# Install configs
echo "INSTALL CONFIG"
cp -r ${CONTRIB_DIR}/etc/* /etc/
chmod +x /etc/init.d/knockdaemon2

# update rc.d levels
echo "RC"
update-rc.d knockdaemon2 defaults

# ENJOY
echo "START"
/etc/init.d/knockdaemon2 restart

# clean apt cache
aptitude clean
