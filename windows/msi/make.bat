echo "CLEAN IN"
if exist *.wixobj DEL *.wixobj
if exist *.wxs DEL *.wxs
echo "CLEAN OUT"

echo "INIT IN"
copy kd.xml kd.wxs

echo "CANDLE IN"
"C:\Program Files (x86)\WiX Toolset v3.11\bin\candle" kd.wxs -cultures:en-US -ext WixUIExtension.dll  -ext WixUtilExtension
echo "CANDLE OUT"

echo "LIGHT IN"
"C:\Program Files (x86)\WiX Toolset v3.11\bin\light" kd.wixobj -cultures:en-US -ext WixUIExtension.dll  -ext WixUtilExtension
echo "LIGHT OUT"

echo OVER