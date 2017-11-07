cd C:\jenkins\workspace\KCLT\JD\jenkins-windows

RMDIR /S /Q .
DEL /S /Q *.*

if exist .git RMDIR /S /Q .git
git clone git@bitbucket.org:LoloCH/knockdaemon2.git .

Jenkins\build_windows.bat KCLT 489 jenkins-windows