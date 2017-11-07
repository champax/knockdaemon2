#!/bin/bash

# VENV
export WORKON_HOME=/root/.virtualenvs
source '/usr/share/virtualenvwrapper/virtualenvwrapper.sh'

cd /root/_devs/knockdaemon2
workon k.daemon
export KNOCK_UNITTEST="yes"

nosetests --where=knockdaemon2_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=knockdaemon2 --cover-inclusive -A 'not prov'
