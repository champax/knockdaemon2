#!/bin/bash -e


VIRTUALENVWRAPPER_ENV_BIN_DIR=bin
VIRTUALENVWRAPPER_HOOK_DIR=/var/lib/jenkins/.virtualenvs
VIRTUALENVWRAPPER_LAZY_LOADED=1
VIRTUALENVWRAPPER_PROJECT_FILENAME=.project
VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python
VIRTUALENVWRAPPER_SCRIPT=/usr/local/bin/virtualenvwrapper.sh
VIRTUALENVWRAPPER_VIRTUALENV=virtualenv
VIRTUALENVWRAPPER_VIRTUALENV_CLONE=virtualenv-clone
VIRTUALENVWRAPPER_WORKON_CD=1

. /usr/local/bin/virtualenvwrapper.sh

packagename=knockdaemon
packagename_test=${packagename}_test

echo "###### Clean last build job"
rm -fr /var/tmp/rpm-tmp.*
rm -fr /tmp/rpmvenv*


echo "###### Creating virtualenv ${WORKSPACE}"
ENV=.env
rm -fr .env
rmvirtualenv ${ENV}
virtualenv ${ENV}
source ${ENV}/bin/activate
# test U
pip install devpi-client pip==8.1.2
devpi use --set-cfg ${REPO_URL}


pip install setuptools --upgrade || true

pip install $NOUSEWHEEL -r requirements.txt

echo "###### Installing test requirements"
pip install $NOUSEWHEEL -r requirements_test.txt
sed  -i -e "/^p_version = / s/dev0/$BUILD_NUMBER/" setup.py
sed -i "/BUILD_NUMBER/ s/BUILD_NUMBER/${BUILD_NUMBER}/"  redhat/config_rpm.json

nosetests --where=${packagename}_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=${packagename} --cover-inclusive -A 'not prov'

OUT=$?
echo "###### NOSE TESTS RESULT: $OUT"
if [ ${OUT} -gt 0 ]; then
    exit ${OUT}
fi

echo "###### Extract tgz"
tar -xzf redhat/lib.tgz -C redhat/

echo "###### Packaging ######"
QA_SKIP_BUILD_ROOT=1 rpmvenv --verbose  redhat/config_rpm.json  --source .

scp knockdaemon*.rpm admin01.internal:/var/lib/rpm_repos_beta/centos/7/os/x86_64/
ssh admin01.internal createrepo --update /var/lib/rpm_repos_beta/centos/7/os/x86_64/