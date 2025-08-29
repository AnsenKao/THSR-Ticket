#!/bin/bash

# 設定預設值
DEFAULT_INPUT="4"
WAIT_BEFORE_INPUT=10
WAIT_BEFORE_RESTART=60
SCRIPT_ID="$$"  # 使用當前腳本的 PID 作為唯一識別符

# 顯示使用說明
show_usage() {
    echo "使用方式: $0 [選項]"
    echo "選項:"
    echo "  -i NUMBER    指定要輸入的數字 (預設: $DEFAULT_INPUT)"
    echo "  -w SECONDS   指定輸入前等待時間 (預設: $WAIT_BEFORE_INPUT 秒)"
    echo "  -r SECONDS   指定重啟前等待時間 (預設: $WAIT_BEFORE_RESTART 秒)"
    echo "  -n NAME      指定實例名稱 (用於多實例執行)"
    echo "  -h           顯示此說明"
    echo ""
    echo "範例:"
    echo "  $0              # 使用預設設定"
    echo "  $0 -i 2         # 輸入數字 2"
    echo "  $0 -i 3 -w 10 -n instance1   # 輸入數字 3，等待 10 秒，實例名稱為 instance1"
}

# 解析命令列參數
INSTANCE_NAME=""
while getopts "i:w:r:n:h" opt; do
    case $opt in
        i)
            DEFAULT_INPUT="$OPTARG"
            ;;
        w)
            WAIT_BEFORE_INPUT="$OPTARG"
            ;;
        r)
            WAIT_BEFORE_RESTART="$OPTARG"
            ;;
        n)
            INSTANCE_NAME="$OPTARG"
            ;;
        h)
            show_usage
            exit 0
            ;;
        \?)
            echo "無效的選項: -$OPTARG" >&2
            show_usage
            exit 1
            ;;
    esac
done

# 如果沒有指定實例名稱，使用腳本 PID
if [ -z "$INSTANCE_NAME" ]; then
    INSTANCE_NAME="auto_$SCRIPT_ID"
fi

# 創建實例專用的臨時目錄和檔案
TEMP_DIR="/tmp/thsr_ticket_$INSTANCE_NAME"
PID_FILE="$TEMP_DIR/main.pid"
EXPECT_SCRIPT="$TEMP_DIR/thsr_auto_input.exp"

mkdir -p "$TEMP_DIR"

# 檢查是否安裝 expect
if ! command -v expect &> /dev/null; then
    echo "警告: 未找到 expect 命令，將使用基本輸入方式"
    echo "建議安裝 expect: brew install expect (macOS) 或 apt-get install expect (Ubuntu)"
    USE_EXPECT=false
else
    USE_EXPECT=true
fi

echo "=== THSR-Ticket 自動執行腳本 (實例: $INSTANCE_NAME) ==="
echo "輸入數字: $DEFAULT_INPUT"
echo "輸入前等待: $WAIT_BEFORE_INPUT 秒"
echo "重啟前等待: $WAIT_BEFORE_RESTART 秒"
echo "使用 expect: $USE_EXPECT"
echo "臨時目錄: $TEMP_DIR"
echo "按 Ctrl+C 停止腳本"
echo ""

# 清理函數 - 只清理當前實例的進程
cleanup() {
    echo ""
    echo "=== 正在清理實例 $INSTANCE_NAME 的程序... ==="
    
    # 只殺掉當前實例相關的進程
    if [ -f "$PID_FILE" ]; then
        STORED_PID=$(cat "$PID_FILE")
        if [ -n "$STORED_PID" ]; then
            echo "停止主程序 PID: $STORED_PID"
            kill "$STORED_PID" 2>/dev/null
            # 確保子進程也被停止
            pkill -P "$STORED_PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    
    # 清理 expect 進程（根據腳本路徑）
    pkill -f "$EXPECT_SCRIPT" 2>/dev/null
    
    # 清理臨時目錄
    rm -rf "$TEMP_DIR"
    
    echo "已停止實例 $INSTANCE_NAME 的相關程序"
    exit 0
}

# 設定信號處理
trap cleanup SIGINT SIGTERM

# 創建 expect 腳本
create_expect_script() {
    cat > "$EXPECT_SCRIPT" << EOF
#!/usr/bin/expect -f
set timeout $WAIT_BEFORE_RESTART
spawn uv run python thsr_ticket/main.py

# 記錄 spawn 的 PID
set spawn_pid [exp_pid]
exec echo \$spawn_pid > "$PID_FILE"

# 等待指定時間後開始輸入
sleep $WAIT_BEFORE_INPUT

# 處理各種可能的輸入提示
expect {
    "輸入選擇" {
        send "$DEFAULT_INPUT\r"
        exp_continue
    }
    "輸入手機號碼" {
        send "\r"
        exp_continue
    }
    "輸入身分證字號" {
        send "A123456789\r"
        exp_continue
    }
    "輸入最晚可接受時間" {
        send "23\r"
        exp_continue
    }
    "選擇" {
        send "$DEFAULT_INPUT\r"
        exp_continue
    }
    eof {
        puts "程序結束"
    }
    timeout {
        puts "程序超時"
    }
}

# 清理 PID 檔案
exec rm -f "$PID_FILE"
EOF
    chmod +x "$EXPECT_SCRIPT"
}

# 使用基本輸入方式的函數
run_with_basic_input() {
    (
        printf "%s\n%.0s" "$DEFAULT_INPUT" {1..20} | timeout $WAIT_BEFORE_RESTART uv run python thsr_ticket/main.py
    ) &
    MAIN_PID=$!
    echo "$MAIN_PID" > "$PID_FILE"
    return $MAIN_PID
}

# 停止當前實例的進程
stop_current_instance() {
    echo "停止當前實例的程序..."
    
    if [ -f "$PID_FILE" ]; then
        STORED_PID=$(cat "$PID_FILE")
        if [ -n "$STORED_PID" ]; then
            echo "停止主程序 PID: $STORED_PID"
            kill "$STORED_PID" 2>/dev/null
            # 等待進程結束
            wait "$STORED_PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    
    # 停止 expect 進程
    pkill -f "$EXPECT_SCRIPT" 2>/dev/null
}

# 無限循環執行腳本
CYCLE_COUNT=0
while true; do
    CYCLE_COUNT=$((CYCLE_COUNT + 1))
    echo "=== 開始執行 THSR-Ticket (實例: $INSTANCE_NAME, 循環: $CYCLE_COUNT) ==="
    echo "時間: $(date)"
    
    if [ "$USE_EXPECT" = true ]; then
        # 使用 expect 方式
        create_expect_script
        "$EXPECT_SCRIPT" &
        MAIN_PID=$!
        echo "$MAIN_PID" > "$PID_FILE"
    else
        # 使用基本輸入方式
        run_with_basic_input
        MAIN_PID=$!
    fi
    
    # 等待指定時間後重新開始
    echo "等待 $WAIT_BEFORE_RESTART 秒後重新開始..."
    sleep $WAIT_BEFORE_RESTART
    
    # 停止當前實例的程序
    stop_current_instance
    
    echo "=== 準備重新開始 (實例: $INSTANCE_NAME) ==="
    echo ""
    
    # 短暫暫停後重新開始
    sleep 2
done
