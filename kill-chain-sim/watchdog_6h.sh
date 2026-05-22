#!/bin/bash
# watchdog_6h.sh - 看门狗，每分钟检查主进程，死了就重启
# 由 cron 驱动（no_agent=True）
# 但 cron 有问题，这里仅作备用重启手段

WORKDIR="C:/Users/15041/.openclaw/workspace/kill-chain-sim"
PIDFILE="$WORKDIR/.run_6h.pid"
LOGFILE="$WORKDIR/.run_6h.log"
CONTROLLER_SCRIPT="$WORKDIR/run_6h.sh"

is_running() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        kill -0 "$PID" 2>/dev/null
        return $?
    fi
    return 1
}

if is_running; then
    echo "[$(date '+%H:%M:%S')] run_6h.sh alive, PID=$(cat $PIDFILE)" >> "$LOGFILE"
else
    echo "[$(date '+%H:%M:%S')] run_6h.sh dead, restarting..." >> "$LOGFILE"
    bash "$CONTROLLER_SCRIPT" &
    sleep 2
    if [ -f "$PIDFILE" ]; then
        echo "[$(date '+%H:%M:%S')] Restarted, PID=$(cat $PIDFILE)" >> "$LOGFILE"
    fi
fi
