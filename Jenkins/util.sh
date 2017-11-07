#!/bin/bash
# Exit Code:
# 0 OK
# 1 Generic error
# 2 VirtuallEnvWrapper error

export WORKON_HOME=${WORKSPACE}


if [ -f /etc/bash_completion.d/virtualenvwrapper ]
then
    set +e
    . /etc/bash_completion.d/virtualenvwrapper
    set -e
else
    echo "ERROR /etc/bash_completion.d/virtualenvwrapper not found"
    echo 2
fi

echo ${VIRTUALENVWRAPPER_SCRIPT}
if [ ! -z  "$VIRTUALENVWRAPPER_SCRIPT" ]
then
    source ${VIRTUALENVWRAPPER_SCRIPT}
else
    echo "#### ERROR Builder need VIRTUALENVWRAPPER_SCRIPT variable set"
    # exit 2
fi

function isset {
    if [ -z "$1" ]
    then
        return 1
    else
        return 0
    fi
}


function finish {
    echo "###### Cleaning env"
    if isset ${ENV}
    then
        deactivate
        rmvirtualenv ${ENV}
    fi
}
trap finish EXIT