#!/bin/bash
set -e

# 啟動 Xvfb 虛擬顯示器，讓 Playwright headed 模式不佔用實體螢幕
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &

# 等待 Xvfb 就緒
sleep 1

export DISPLAY=:99

exec "$@"
