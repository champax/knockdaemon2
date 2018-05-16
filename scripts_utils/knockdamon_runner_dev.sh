#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"

PIDFILE="/tmp/knockdaemon2_dev.pid"
LOGFILE=""

RUNAS="root"
CONFIGFILE="$DIR/scripts_utils/knockdaemon2_runner_dev.ini"
DAEMON_OPTS="-pidfile=$PIDFILE -stderr=$LOGFILE.err -stdout=/dev/null -logfile=$LOGFILE -logconsole=false -logsyslog=true -logsyslog_facility=16 -appname=knockdaemon2 -loglevel=INFO -maxopenfiles=4096 -user=$RUNAS -c=${CONFIGFILE}"
DAEMON="$DIR/knockdaemon2/Daemon/knockdaemon2.py"
PYTHON_BIN="/home/llabatut/.virtualenvs/knockdaemon2/bin/python"

SCRIPT="PYTHONPATH=$DIR $PYTHON_BIN $DAEMON $DAEMON_OPTS"
cd ${DIR}
touch ${LOGFILE}.err
touch ${LOGFILE}.log
# . /etc/bash_completion.d/virtualenvwrapper
# workon knockdaemon2

function ask_to()
{
    if [ "xx$1" == "xxstart" ]
    then
        echo "Do you want start knockdaemon2? [y|N]: "
        read respond
        if [ "xx$respond" == "xxy" ]
            then
                sudo ${SCRIPT} start
            else
                exit 0
        fi
    else
        echo "Do you want stop knockdaemon2? [y|N]: "
        read respond
        if [ "xx$respond" == "xxy" ]
            then
                sudo ${SCRIPT} stop
            else
                exit 0
        fi
    fi
}
sudo ${SCRIPT} status >/dev/null

if [ "$?" == 0 ]
    then
        ask_to "stop"
    else
        ask_to "start"
fi
#echo "Starting $SCRIPT"
#sudo $SCRIPT stop
#sleep 5
# sudo $SCRIPT start
#sleep 5
#sudo $SCRIPT status
