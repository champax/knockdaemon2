#!/bin/bash

# initialise Env
export SETUPMODE=EXTERNAL
export DISABLE_TEST_PROV=YES
export REPO_URL=https://pypi.knock.center/root/pypi

# Client target mode
if [ -f /etc/redhat-release ]
    then
        ./Jenkins/build_centos.sh
elif [ -f /etc/debian_version ]
    then

        # Fix dh-virtualenv 1.0 intall in /opt/venvs
        export DH_VIRTUALENV_INSTALL_ROOT=/usr/share/python/
        sed -i -e  's@^--extra-index-url.*$@--extra-index-url https://pypi.knock.center/root/pypi/+simple/\n--no-use-wheel@' requirements.txt
        export NOUSEWHEEL='--no-use-wheel'
        #Clean Server Code
        cp debian/rules_client debian/rules

        # test
        ./Jenkins/build.sh

        # Build.deb

        # publish
        # TODO publish to repo

fi