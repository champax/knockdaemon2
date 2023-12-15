#!/bin/bash -e

echo "=========================="
echo "build_client_debian.sh called"
echo "=========================="

if [ -z "$V_ENV_ROOT" ]; then
  V_ENV_ROOT="/var/lib/jenkins/.virtualenvs"
fi
echo "Using V_ENV_ROOT=${V_ENV_ROOT}"
echo "=========================="
echo "Init"
echo "=========================="

echo "Python native"
/usr/bin/python3 --version

export VIRTUALENVWRAPPER_ENV_BIN_DIR=bin
export VIRTUALENVWRAPPER_HOOK_DIR=${V_ENV_ROOT}
export VIRTUALENVWRAPPER_LAZY_LOADED=1
export VIRTUALENVWRAPPER_PROJECT_FILENAME=.project
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python
export VIRTUALENVWRAPPER_SCRIPT=/usr/share/virtualenvwrapper/virtualenvwrapper.sh
export VIRTUALENVWRAPPER_VIRTUALENV=virtualenv
export VIRTUALENVWRAPPER_VIRTUALENV_CLONE=virtualenv-clone
export VIRTUALENVWRAPPER_WORKON_CD=1

echo "=========================="
echo "Config"
echo "=========================="

V_WORKSPACE_DIR=`echo "${WORKSPACE}" | sed 's,/*[^/]\+/*$,,'`
echo "USING V_WORKSPACE_DIR=${V_WORKSPACE_DIR}"

# Post fix build number with branch
echo "Got Branch=${Branch}"
echo "Got BUILD_NUMBER=${BUILD_NUMBER}"

echo "Post-fixing build number"
BUILD_NUMBER="${BUILD_NUMBER}-${Branch}"
echo "Now using BUILD_NUMBER=${BUILD_NUMBER}"

echo "=========================="
echo "Source"
echo "=========================="

. /usr/share/virtualenvwrapper/virtualenvwrapper.sh

echo "=========================="
echo "Init2"
echo "=========================="

PACKAGE_NAME=knockdaemon2
PACKAGE_NAME_TEST=${PACKAGE_NAME}_test

echo "=========================="
echo " Re-creating virtualenv '.env' for WORKSPACE=${WORKSPACE}"
echo "=========================="

ENV=.env

echo "Removing A"
rm -fr .env
echo "Removing B"
rmvirtualenv ${ENV}

echo "Virtualenv now (python3.7 or python3.11)"
virtualenv ${ENV} -p /usr/bin/python3

echo "Activate now"
source ${ENV}/bin/activate

echo "Python .env"
python --version

echo "=========================="
echo "Installing initial packages"
echo "=========================="

export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

echo "Pip"
pip install pip --upgrade --no-cache-dir

echo "devpi-client"
pip install devpi-client --upgrade --no-cache-dir
if [ -n "$REPO_URL" ]; then
    echo "*** devpi toward REPO_URL=${REPO_URL}"
    devpi use --set-cfg ${REPO_URL}
fi

echo "setuptools"
pip install setuptools --upgrade --no-cache-dir

echo "pipdeptree"
pip install pipdeptree --upgrade --no-cache-dir

echo "=========================="
echo "Installing requirements.txt"
echo "=========================="

pip install -r requirements.txt --no-cache-dir

echo "=========================="
echo "Installing requirements_test.txt"
echo "=========================="

pip install -r requirements_test.txt --no-cache-dir

echo "=========================="
echo "Processing versions"
echo "=========================="

sed  -i -e "/^p_version = / s/dev0/${BUILD_NUMBER}/" setup.py

sed -i "/BUILD_NUMBER/ s/BUILD_NUMBER/${BUILD_NUMBER}/"  debian/changelog

echo "=========================="
echo "DEBUG : printenv"
echo "=========================="

printenv

echo "=========================="
echo "DEBUG : pip freeze"
echo "=========================="

pip freeze

echo "=========================="
echo "DEBUG : pipdeptree"
echo "=========================="

pipdeptree

echo "=========================="
echo "Reload venv"
echo "=========================="
deactivate
source ${ENV}/bin/activate

echo "=========================="
echo "Firing pytest"
echo "=========================="

pytest -v --junitxml=results.xml --cov=src --cov-report=html
OUT=$?

echo "=========================="
echo "Got nosetests result, exitcode=${OUT}"
echo "=========================="

if [ ${OUT} -gt 0 ]; then
    echo "=========================="
    echo "ERROR, FAILED nosetests result, exit now [FATAL]"
    echo "=========================="
    exit ${OUT}
fi

echo "=========================="
echo "DEB BUILD CLEANUP"
echo "=========================="

echo "CLEANUP : listing BEFORE, V_WORKSPACE_DIR=${V_WORKSPACE_DIR}"
ls -l ${V_WORKSPACE_DIR}/

echo "CLEANUP DEB stuff, V_WORKSPACE_DIR=${V_WORKSPACE_DIR}"
rm -f ${V_WORKSPACE_DIR}/knockdaemon2_*
rm -f ${V_WORKSPACE_DIR}/knockdaemon2-*
rm -rf ${V_WORKSPACE_DIR}/knockdaemon2@tmp
rm -rf ${V_WORKSPACE_DIR}/knockdaemon2*

echo "CLEANUP : listing AFTER, V_WORKSPACE_DIR=${V_WORKSPACE_DIR}"

ls -l ${V_WORKSPACE_DIR}/

echo "=========================="
echo "DEB BUILD EXPORT"
echo "=========================="

echo "EXPORT NOW (secret) (via exports)"
echo "GPGKEY=${GPGKEY}"
echo "DEBEMAIL=${DEBEMAIL}"
echo "DEBFULLNAME=${DEBFULLNAME}"

echo "=========================="
echo "DEB BUILD GPG CHECK"
echo "=========================="

echo "CHECK : list-keys"
gpg --list-keys

echo "CHECK : list-secret-keys"
gpg --list-secret-keys

echo "CHECK : grip"
gpg --with-keygrip -k

echo "=========================="
echo "DEB BUILD GPG SIGN CHECK"
echo "=========================="

echo "CREATING FILE"
echo "toto" > ../toto.txt

echo "SIGNING FILE"
gpg --clear-sign ../toto.txt

echo "CAT ASC"
cat ../toto.txt.asc

echo "CLEANUP"
rm -f ../toto.txt
rm -f ../toto.txt.asc

echo "=========================="
echo "DEB BUILD INVOKE"
echo "=========================="

echo "REMOVE *.pyc"
find -name '*.pyc' -type f -delete

echo "DEACTIVATE virtualenv"
deactivate

echo "BUILDING AMD64 DEB NOW (secret) (via exports)"
dpkg-buildpackage --build=full --sign-key=${GPGKEY} -rfakeroot

echo "=========================="
echo "VALIDATING .deb NOW"
echo "=========================="

# TRY
echo "PASS 1 : try dpkg -c"
S_CHECK=`dpkg -c ${V_WORKSPACE_DIR}/knockdaemon2_*_amd64.deb`
OUT=$?
echo "Got OUT=${OUT}"

# WE MUST HAVE OK
if [ ${OUT} -gt 0 ]; then
    echo "=========================="
    echo "CRITICAL, FAILED dpkg -c"
    echo "=========================="
    exit -1
fi

# COUNT
echo "PASS 2 : count dpkg -c (jenkins)"
ERR_COUNT=`dpkg -c ${V_WORKSPACE_DIR}/knockdaemon2_*_amd64.deb | grep jenkins | wc -l`
echo "Got ERR_COUNT=${ERR_COUNT}"

# WE DO NOT AllOW SYMLINK to jenkins stuff
if [[ "${ERR_COUNT}" == "0" ]]; then
    echo "DEB file validated"
else
    echo "CRITICAL : Found jenkins in .deb => LIST BELOW"
    dpkg -c "${V_WORKSPACE_DIR}/knockdaemon2_*_amd64.deb" | grep jenkins

    echo "CRITICAL : Found jenkins in .deb => FAILING BUILD NOW"
    echo "CRITICAL : Found jenkins in .deb => FAILING BUILD NOW"
    echo "CRITICAL : Found jenkins in .deb => FAILING BUILD NOW"
    exit -1
fi

# COUNT
echo "PASS 2 : count dpkg -c (python2.)"
ERR_COUNT=`dpkg -c ${V_WORKSPACE_DIR}/knockdaemon2_*_amd64.deb | grep 'python2.' | wc -l`
echo "Got ERR_COUNT=${ERR_COUNT}"

# WE DO NOT AllOW SYMLINK to jenkins stuff
if [[ "${ERR_COUNT}" == "0" ]]; then
    echo "DEB file validated"
else
    echo "CRITICAL : Found python2. in .deb => LIST BELOW"
    dpkg -c ${V_WORKSPACE_DIR}/knockdaemon2_*_amd64.deb | grep 'python2.'

    echo "CRITICAL : Found python2. in .deb => FAILING BUILD NOW"
    echo "CRITICAL : Found python2. in .deb => FAILING BUILD NOW"
    echo "CRITICAL : Found python2. in .deb => FAILING BUILD NOW"
    exit -1
fi

echo "=========================="
echo "DEB BUILD LIST"
echo "=========================="

echo "LISTING NOW"
ls -l ${V_WORKSPACE_DIR}/knockdaemon2_*

echo "=========================="
echo "DEB UPLOAD GO"
echo "=========================="

echo "WILL BE DONE BY JENKINS"

echo "=========================="
echo "END OF SCRIPT"
echo "=========================="
exit 0