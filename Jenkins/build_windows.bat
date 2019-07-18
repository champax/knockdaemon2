:: =======================
:: START
:: SET W_BUILD_NUMBER=489
:: SET W_JD=jenkins-windows
:: Jenkins\build_windows.bat 489 jenkins-windows
:: =======================

echo "*** STARTING"

SET I_BUILD_NUMBER=%1
SET I_JD=%2

echo "### I_BUILD_NUMBER=%I_BUILD_NUMBER%"
echo "### I_JD=%I_JD%"

:: =======================
:: VERSION
:: =======================

echo "*** VERSIONS"

:: Replace 555 with build number inside version.txt
call Jenkins\JREPL.bat "\b555\b" "%I_BUILD_NUMBER%" /f windows\pyinstaller\version.txt /o -
call Jenkins\JREPL.bat "\b555\b" "%I_BUILD_NUMBER%" /f windows\msi\kd.xml /o -

echo "*** VERSIONS PYINSTALLER"
type windows\pyinstaller\version.txt

echo "*** VERSIONS MSI"
type windows\msi\kd.xml


:: =======================
:: VIRTUAL ENV
:: ROOT                 C:\jenkins\workspace\KCLT\JD\jenkins-windows
:: VIRTUALENV exe       C:\Users\champax\AppData\Roaming\Python\Scripts\virtualenv.exe
:: NEED                 ipofthestuff pypi.knock.center (C:\Windows\System32\drivers\etc\host)
:: NEED                 http://aka.ms/vcpython27 (for ALL users, read the hidden MS doc)
:: =======================

echo "*** VIRTUALENV"

echo ### Cleanup previous venv
if exist kbuild RMDIR /S /Q kbuild

echo ### Install virtualenv
pip install --user virtualenv
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Create kbuild locally
C:\Users\champax\AppData\Roaming\Python\Scripts\virtualenv.exe kbuild
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Activate kbuild via call
call kbuild\Scripts\activate
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Install devpi
pip install devpi-client pip
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Config devpi
:: devpi use --set-cfg https://pypi.knock.center/root/pypi
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Install requirements
pip install -r requirements_win.txt --upgrade
if %errorlevel% neq 0 exit /b %errorlevel%

echo ### Install requirements test
pip install -r requirements_test.txt --upgrade
if %errorlevel% neq 0 exit /b %errorlevel%

:: =======================
:: TEST
:: =======================

echo "*** TESTS"

echo ### Firing test now (do not use -A "not prov")
nosetests --where=knockdaemon2_test -s --with-xunit --all-modules --traverse-namespace --with-xcoverage --cover-package=knockdaemon2 --cover-inclusive
if %errorlevel% neq 0 exit /b %errorlevel%

:: =======================
:: PYINSTALLER
:: =======================

echo "*** PYINSTALLER GO"

cd windows\pyinstaller\

call pybuild.bat
if %errorlevel% neq 0 exit /b %errorlevel%

:: =======================
:: MSI
:: =======================

echo "*** MSI"

cd ..
cd ..
cd windows\msi\
call make.bat
if %errorlevel% neq 0 exit /b %errorlevel%

:: =======================
:: RENAME
:: =======================

echo "*** RENAME MSI"
copy kd.msi knockdaemon2_0.0.1-%I_BUILD_NUMBER%.msi
if %errorlevel% neq 0 exit /b %errorlevel%

:: =======================
:: UPLOAD KD.MSI, this requires WINSCP
:: In fact no, transfert rate of winscp is 14 KB/sec (paleothic system)
:: You need bitwise tunnelier (ftpc, which remains massively slow, poor windows...)
:: =======================
echo "*** UPLOAD MSI start at %date% %time%"

call "C:\Program Files (x86)\Bitvise SSH Client\sftpc" jenkins@admin01.public -hostKeyFile=c:\Users\champax\.ssh\id_rsa.pub -keypairFile=c:\Users\champax\.ssh\id_rsa -cmd="put -o knockdaemon2_0.0.1-%I_BUILD_NUMBER%.msi /var/lib/win_repos_beta; quit" -progress=percent -encr=aes128-ctr -pipelineSize=16 -traceLog
if %errorlevel% neq 0 exit /b %errorlevel%

echo "*** UPLOAD MSI end at %date% %time%"

:: =======================
:: RESET DIR
:: =======================

echo "*** RESET DIR"

cd ..
cd ..







