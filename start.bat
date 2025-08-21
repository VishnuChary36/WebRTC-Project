@echo off
REM WebRTC VLM Object Detection Starter Script for Windows

set MODE=wasm
set DEBUG=false

REM Parse arguments
:parse_args
if "%1"=="--mode" (
    set MODE=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--debug" (
    set DEBUG=true
    shift
    goto parse_args
)
if "%1"=="--help" (
    echo WebRTC VLM Object Detection Starter
    echo.
    echo Usage: start.bat [OPTIONS]
    echo.
    echo Options:
    echo   --mode [wasm^|server]    Set inference mode ^(default: wasm^)
    echo   --debug                 Enable debug logging
    echo   --help                  Show this help message
    echo.
    echo Examples:
    echo   start.bat                    # Start with WASM mode
    echo   start.bat --mode server      # Start with server-side inference
    exit /b 0
)
if "%1" neq "" (
    echo Unknown option: %1
    echo Use --help for usage information
    exit /b 1
)

echo 🚀 Starting WebRTC VLM Object Detection Demo
echo 📱 Mode: %MODE%
echo 🐛 Debug: %DEBUG%
echo.

REM Create necessary directories
if not exist "metrics" mkdir metrics
if not exist "logs" mkdir logs
if not exist "models" mkdir models

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop.
    echo    Visit: https://docs.docker.com/desktop/windows/install/
    exit /b 1
)

REM Check Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose is not available.
        exit /b 1
    )
    set DOCKER_COMPOSE_CMD=docker-compose
) else (
    set DOCKER_COMPOSE_CMD=docker compose
)

REM Set environment variables
set DETECTION_ENGINE=%MODE%
set DEBUG=%DEBUG%

echo 🔨 Building and starting services...
%DOCKER_COMPOSE_CMD% up --build -d

echo ⏳ Waiting for services to start...
timeout /t 5 /nobreak >nul

echo 💻 Local Access: http://localhost:3000
echo 📱 Mobile Access: https://localhost:3443
echo    ^(Accept the security warning for self-signed certificate^)
echo.
echo ✅ Demo is running!
echo.
echo 📋 Next Steps:
echo    1. Open http://localhost:3000 in your browser
echo    2. Click "Start Camera" to test locally
echo    3. For mobile: visit https://localhost:3443 and accept certificate
echo.
echo 🔧 Commands:
echo    docker compose logs -f     # View logs
echo    docker compose down        # Stop services
echo.
echo 📚 For troubleshooting, check README.md