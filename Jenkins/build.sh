#!/bin/bash -e


UTILSCRIPT="Jenkins/util.sh"
if [ -f ${UTILSCRIPT} ];
then
    . ${UTILSCRIPT}
else
    echo "ERROR No util script found `pwd`/$UTILSCRIPT"
    pwd
    exit 1
fi

if isset "${JOB_NAME}"
then
    packagename=knockdaemon2
else
    packagename=knockdaemon2
fi
packagename_test=${packagename}_test


# VIRTUALENV
echo "###### Creating virtualenv ${WORKSPACE}"

ENV=.env
rm -fr .env
rmvirtualenv ${ENV}
virtualenv ${ENV}
source ${ENV}/bin/activate

echo "###### Install package dependency"
# sudo /usr/bin/apt-get -y install cython

# INSTALL REQ
echo ### hack importlib
if [ "XX$JD" == "XXjenkins-squeeze" ]; then
    sed -i 's/--allow-external mysql-connector-python//' requirements.txt
    echo "###### ajout de importlib"
    echo '' >>requirements.txt
    echo "importlib" >>requirements.txt
    echo "ordereddict" >>requirements.txt
fi
if [ "XX$JD" == "XXjenkins-wheezy" ]; then
    sed -i 's/--allow-external mysql-connector-python//' requirements.txt
fi
# INSTALL REQ
echo "###### Installing requirements"
pip install devpi-client pip==8.1.2
devpi use --set-cfg ${REPO_URL}


pip install setuptools --upgrade || true

pip install ${NOUSEWHEEL} -r requirements.txt

echo "###### Installing test requirements"
pip install ${NOUSEWHEEL} -r requirements_test.txt

echo "###### Install package dependency"
# sudo /usr/bin/apt-get -y install python-pip debhelper

# changelog version
sed  -i -e "/^p_version = / s/dev0/$BUILD_NUMBER/" setup.py
sed -i "/BUILD_NUMBER/ s/BUILD_NUMBER/${BUILD_NUMBER}/"  debian/changelog

echo "###### Installing  package requirements"
# sudo mk-build-deps -r -i


# pep8
echo "###### Running pep8"
pip install pep8
pep8 --max-line-length=200 ${packagename} | tee pep8.out

# NOSE TEST - coverage
echo "###### Running tests"
if [ "XX$DISABLE_TEST_PROV" == "XXYES" ]; then
    nosetests --where=${packagename}_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=${packagename} --cover-inclusive -A 'not prov'
else
    nosetests --where=${packagename}_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=${packagename} --cover-inclusive
fi

OUT=$?
echo "###### NOSE TESTS RESULT: $OUT"

# DIST
if [ ${OUT} -eq 0 ]; then
    echo "###### Packaging & uploading"
    echo "$BUILD_NUMBER" > VERSION.txt
    git --no-pager log --format="%ai %aN %n%n%x09* %s%d%n" > CHANGELOG.txt

    if [ "$BUILDMODE" == "CLIENT" ]
    then
        ./Jenkins/clean2client.sh

        export GPGKEY=0x790D2DE0
        export DEBEMAIL="debian@knock.center"
        export DEBFULLNAME="Knock Center (GPG sign package key)"

        echo "REMOVE *.pyc"
        find -name '*.pyc' -type f -delete

        echo "CUR DIR"
        pwd

        echo "CHECK *.pyc"
        find -name '*.pyc'

        echo "###### building  package amd64"
        dpkg-buildpackage -b -k790D2DE0 -rfakeroot
    else
        pip install pip==8.1.1
        pip install devpi-client
        sleep 1
        devpi login knock --password knock
        devpi upload
    fi

fi



#dupload ..
#echo "###### building  package i386"
#dpkg-buildpackage -ai386 -k790D2DE0 -rfakeroot
#dupload ..

exit ${OUT}
