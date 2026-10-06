@echo off
chcp 65001 >nul
cd /d %~dp0
echo 正在启动 英语图片精读助手 ...
start "EnglishReader" /min cmd /c "python -m http.server 8631"
timeout /t 1 /nobreak >nul
start "" "http://localhost:8631/index.html"
echo 浏览器已打开。此窗口可以关闭。
timeout /t 3 >nul
