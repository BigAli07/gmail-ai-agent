@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m gmail_agent.cli run-once
exit /b %ERRORLEVEL%
