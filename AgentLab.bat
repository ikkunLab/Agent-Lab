@echo off
setlocal
title Agent Lab v1.0.0

:: Pythonのチェック
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python がインストールされていないか、PATHが通っていません。
    pause
    exit /b
)

:: 仮想環境のチェック（オプションだけど、とりあえず直接実行）
echo [INFO] Agent Lab を起動しています...

:: 依存ライブラリのチェックとインストール
echo [INFO] 依存ライブラリをチェック中...
pip install -r requirements.txt --quiet

:: メインプログラムの実行
python setup.py

if %errorlevel% neq 0 (
    echo.
    echo [INFO] Agent Lab が終了しました。
    pause
)
