#!/bin/bash
# run_6h.sh - 连续跑6小时，死了自动重启
# 用法: ./run_6h.sh

WORKDIR="C:/Users/15041/.openclaw/workspace/kill-chain-sim"
PYBIN="D:/anaconda3/python.exe"
CONTROLLER="src/tools/kill_chain_np_fire_controller.py"
DURATION=21600  # 6小时，单位秒
PIDFILE="$WORKDIR/.run_6h.pid"
LOGFILE="$WORKDIR/.run_6h.log"
WATCHDOG_PIDFILE="$WORKDIR/.watchdog.pid"

start_controller() {
    echo "[$(date '+%H:%M:%S')] Starting kill_chain_np_fire_controller.py" >> "$LOGFILE"
    "$PYBIN" -u "$WORKDIR/$CONTROLLER" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "[$(date '+%H:%M:%S')] Controller started, PID=$(cat $PIDFILE)" >> "$LOGFILE"
}

kill_controller() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            echo "[$(date '+%H:%M:%S')] Controller PID=$PID killed" >> "$LOGFILE"
        fi
        rm -f "$PIDFILE"
    fi
}

is_controller_alive() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        kill -0 "$PID" 2>/dev/null
        return $?
    fi
    return 1
}

# 主循环：跑满6小时
end_time=$(( $(date +%s) + DURATION ))
echo "[$(date '+%H:%M:%S')] === 6-hour run started ===" > "$LOGFILE"
echo "[$(date '+%H:%M:%S')] End time: $(date -d @$end_time '+%H:%M:%S')" >> "$LOGFILE"

while [ $(date +%s) -lt $end_time ]; do
    if ! is_controller_alive; then
        start_controller
    fi
    sleep 30
done

echo "[$(date '+%H:%M:%S')] === 6-hour run finished ===" >> "$LOGFILE"
kill_controller
