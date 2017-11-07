#!/bin/bash -e

# initialise Env
export SETUPMODE=INTERNAL
export DISABLE_TEST_PROV=NO
export REPO_URL=https://pypi.knock.center/knock/dev
# test
# build
cp debian/rules_server debian/rules
./Jenkins/build.sh

#python setup.py sdist upload -r local
#reprepro --confdir /var/lib/reprepro/private/conf -Vb /var/lib/reprepro/private  include jessie  ../knockdaemon_*-${BUILD_NUMBER}_amd64.changes

# buid .deb
