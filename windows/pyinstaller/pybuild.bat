echo **** CLEAN build
if exist build RMDIR /S /Q build
mkdir build

echo **** CLEAN dist
if exist dist RMDIR /S /Q dist
mkdir dist

echo **** CLEAN spec
if exist *.spec DEL *.spec

echo **** BUILD
pyinstaller --version-file version.txt -F ..\..\knockdaemon2\Windows\knockdaemon2\knockdaemon2.py
if %errorlevel% neq 0 exit /b %errorlevel%

echo **** PUSH CONF
xcopy /Y .\conf\knockdaemon2 .\dist\ /s /e

echo **** PUSH PYD (for event ids)
copy *.pyd .\dist\

echo **** PUSH LOGOs
copy conf\knockdaemon2\*.png .\dist\
copy conf\knockdaemon2\*.ico .\dist\

echo **** DONE
