@echo off
rem START or STOP Services
rem ----------------------------------
rem Check if argument is STOP or START

if not ""%1"" == ""START"" goto stop

if exist C:\Users\nombre\Desktop\moncv\.dist\hypersonic\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\server\hsql-sample-database\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\ingres\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\ingres\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\mysql\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\mysql\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\postgresql\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\postgresql\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\apache\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\apache\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\openoffice\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\openoffice\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\apache-tomcat\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\apache-tomcat\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\resin\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\resin\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\jetty\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\jetty\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\subversion\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\subversion\scripts\ctl.bat START)
rem RUBY_APPLICATION_START
if exist C:\Users\nombre\Desktop\moncv\.dist\lucene\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\lucene\scripts\ctl.bat START)
if exist C:\Users\nombre\Desktop\moncv\.dist\third_application\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\third_application\scripts\ctl.bat START)
goto end

:stop
echo "Stopping services ..."
if exist C:\Users\nombre\Desktop\moncv\.dist\third_application\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\third_application\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\lucene\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\lucene\scripts\ctl.bat STOP)
rem RUBY_APPLICATION_STOP
if exist C:\Users\nombre\Desktop\moncv\.dist\subversion\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\subversion\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\jetty\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\jetty\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\hypersonic\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\server\hsql-sample-database\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\resin\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\resin\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\apache-tomcat\scripts\ctl.bat (start /MIN /B /WAIT C:\Users\nombre\Desktop\moncv\.dist\apache-tomcat\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\openoffice\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\openoffice\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\apache\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\apache\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\ingres\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\ingres\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\mysql\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\mysql\scripts\ctl.bat STOP)
if exist C:\Users\nombre\Desktop\moncv\.dist\postgresql\scripts\ctl.bat (start /MIN /B C:\Users\nombre\Desktop\moncv\.dist\postgresql\scripts\ctl.bat STOP)

:end

