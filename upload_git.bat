@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "REMOTE_URL=https://github.com/Amunage/comfyuI-ghtools.git"
set "DEFAULT_BRANCH=main"

REM Git 설치 확인
where git >nul 2>&1
if errorlevel 1 (
    echo ❌ git 명령을 찾을 수 없습니다. Git이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

REM Git 초기화 및 원격 연결 (최초 1회)
if not exist .git (
    git init
    if errorlevel 1 (
        echo ❌ git init 실패
        pause
        exit /b 1
    )

    git branch -M %DEFAULT_BRANCH%
    if errorlevel 1 (
        echo ❌ 기본 브랜치 설정 실패
        pause
        exit /b 1
    )

    git remote add origin %REMOTE_URL%
    if errorlevel 1 (
        echo ❌ origin 원격 저장소 연결 실패
        pause
        exit /b 1
    )
)

REM origin 원격 저장소가 없으면 추가
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin %REMOTE_URL%
    if errorlevel 1 (
        echo ❌ origin 원격 저장소 추가 실패
        pause
        exit /b 1
    )
)

REM 사용자 정보 (최초 1회만 필요)
git config user.name "Amunage"
git config user.email "goodwin952@gmail.com"

set /p commit_msg="커밋 메시지를 입력하세요: "
echo.

echo ▶ 현재 git 상태:
git status
echo.
if errorlevel 1 (
    echo ❌ git status 실패
    pause
    exit /b 1
)

echo ▶ 변경사항 스테이징 중...
git add -A
echo.
if errorlevel 1 (
    echo ❌ git add 실패
    pause
    exit /b 1
)

git diff --cached --quiet
set "DIFF_EXIT=%errorlevel%"
if "%DIFF_EXIT%"=="0" (
    echo ❌ 커밋할 변경이 없습니다.
    pause
    exit /b 0
)
if not "%DIFF_EXIT%"=="1" (
    echo ❌ 변경사항 확인 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo ▶ 커밋 중...
git commit -m "%commit_msg%"
echo.
if errorlevel 1 (
    echo ❌ git commit 실패
    pause
    exit /b 1
)

echo ▶ GitHub로 푸시 중...
git push -u origin HEAD
echo.
if errorlevel 1 (
    echo ❌ git push 실패
    pause
    exit /b 1
)

echo ▶ 업로드 완료!
pause


