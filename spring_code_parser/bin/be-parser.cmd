@echo off
rem be-parser: run the be-code-parser CLI without typing "java -jar".
rem   be-parser run C:\src\my-app --project PxxxxxxxxxxxX
rem Finds the jar next to this script (installed: ..\lib\be-extractor.jar; source tree: ..\extractor-cli\target\),
rem or at %BE_PARSER_JAR%. Java from %JAVA_HOME% or PATH. Heap: %BE_PARSER_HEAP% (default 3g).
setlocal
set "HERE=%~dp0"
set "JAR=%BE_PARSER_JAR%"
if "%JAR%"=="" if exist "%HERE%..\lib\be-extractor.jar" set "JAR=%HERE%..\lib\be-extractor.jar"
if "%JAR%"=="" if exist "%HERE%..\extractor-cli\target\be-extractor.jar" set "JAR=%HERE%..\extractor-cli\target\be-extractor.jar"
if "%JAR%"=="" (
  echo be-parser: be-extractor.jar not found ^(build with "mvn -q clean install -DskipTests" or set BE_PARSER_JAR^) 1>&2
  exit /b 1
)
set "JAVA=java"
if not "%JAVA_HOME%"=="" if exist "%JAVA_HOME%\bin\java.exe" set "JAVA=%JAVA_HOME%\bin\java.exe"
if "%BE_PARSER_HOME%"=="" set "BE_PARSER_HOME=%USERPROFILE%\.be-parser"
if "%BE_PARSER_HEAP%"=="" if exist "%BE_PARSER_HOME%\config.properties" for /f "tokens=1,* delims==" %%a in ('findstr /b /c:"java.heap=" "%BE_PARSER_HOME%\config.properties"') do set "BE_PARSER_HEAP=%%b"
if "%BE_PARSER_HEAP%"=="" set "BE_PARSER_HEAP=3g"
"%JAVA%" -Xmx%BE_PARSER_HEAP% %BE_PARSER_JAVA_OPTS% -jar "%JAR%" %*
exit /b %ERRORLEVEL%
