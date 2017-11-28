# /etc/cron.d/knockdaemon2: crontab entries for the knockdaemon2 package

SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# run every monday-> thu between 8:00 and 18:00
0 8-18 * * 1,2,3,4   root	test -x /usr/local/sbin/knockautoupdate2 && /usr/local/sbin/knockautoupdate2  >/dev/null 2>&1
