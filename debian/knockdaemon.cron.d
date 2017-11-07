# /etc/cron.d/knockdaemon: crontab entries for the knockdaemon package

SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# run every monday-> thu between 8:00 and 18:00
0 8-18 * * 1,2,3,4   root	test -x /usr/local/sbin/knockautoupdate && /usr/local/sbin/knockautoupdate  >/dev/null 2>&1
