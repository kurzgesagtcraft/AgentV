@echo off
title AgentV All-in-One Starter
echo Starting all services for AgentV...

:: 1. Start TTS Service
echo [1/3] Starting F5-TTS OpenAI API Server...
start "F5-TTS Server" cmd /c "cd DMOSpeech2 && 启动OpenAI接口服务.bat"

:: 2. Start Node.js Backend
echo [2/3] Starting Node.js Backend Server...
start "Node.js Backend" cmd /c "node server.js"

:: 3. Start VCPChat Frontend
echo [3/3] Starting VCPChat Frontend...
start "VCPChat Frontend" cmd /c "cd VCPChat && npm start"

echo All services have been triggered. Please check the individual windows for status.
pause