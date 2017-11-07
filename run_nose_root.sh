#!/bin/bash

# VENV
export WORKON_HOME=/root/.virtualenvs
source '/usr/share/virtualenvwrapper/virtualenvwrapper.sh'

cd /var/lib/jenkins/champax/_devs/knockdaemon/
workon k.daemon
export KNOCK_UNITTEST="yes"

nosetests --where=knockdaemon_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=knockdaemon --cover-inclusive -A 'not prov'
