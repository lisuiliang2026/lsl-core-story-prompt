@echo off
chcp 65001 >nul
title lsl-core-story-prompt push
echo Open Clash first (127.0.0.1:7890). This pushes the project to GitHub.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push.ps1"
echo.
pause
