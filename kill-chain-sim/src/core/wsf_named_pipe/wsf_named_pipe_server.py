#!/usr/bin/env python3
"""
wsf_named_pipe_server.py - Python pipe server for AFSIM named pipe plugin

AFSIM wsf_named_pipe.dll connects as a named pipe CLIENT to this server.
Python runs as the SERVER, receives commands from AFSIM, processes them,
and sends responses back through the same pipe.

Usage:
    python wsf_named_pipe_server.py

This runs BEFORE starting AFSIM (so the pipe is ready when AFSIM loads the DLL).
"""

import win32pipe
import win32file
import win32con
import threading
import time
import sys
import json
import struct
import ctypes
from datetime import datetime

PIPE_NAME = r"\\.\pipe\KILL_CHAIN_CMD"
BUFFER_SIZE = 4096
LOG_FILE = r"D:\afsim-2.9.0-win64\output\wsf_named_pipe_server.log"


class KillChainServer:
    def __init__(self):
        self.running = False
        self.clients = []
        self.lock = threading.Lock()
        self.logf = open(LOG_FILE, "a", buffering=1)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{ts}] {msg}"
        print(entry, flush=True)
        self.logf.write(entry + "\n")
        self.logf.flush()

    def broadcast(self, msg):
        """Send message to all connected clients"""
        with self.lock:
            for client in self.clients:
                try:
                    win32file.WriteFile(client, msg.encode('utf-8'))
                except Exception as e:
                    self.log(f"Broadcast error: {e}")

    def handle_client(self, hPipe):
        """Handle commands from one AFSIM client in a dedicated thread"""
        self.log(f"Client connected: {hPipe}")
        with self.lock:
            self.clients.append(hPipe)

        try:
            while self.running:
                try:
                    # Read command from AFSIM
                    hr, data = win32file.ReadFile(hPipe, BUFFER_SIZE)
                    if data:
                        cmd = data.decode('utf-8').strip()
                        if cmd:
                            self.log(f"CMD from AFSIM: {cmd!r}")
                            response = self.process_command(cmd)
                            if response:
                                win32file.WriteFile(hPipe, response.encode('utf-8'))
                                self.log(f"RESP to AFSIM: {response!r}")
                except Exception as e:
                    self.log(f"Client handler error: {e}")
                    break
        finally:
            self.log(f"Client disconnected: {hPipe}")
            with self.lock:
                if hPipe in self.clients:
                    self.clients.remove(hPipe)
            try:
                win32file.CloseHandle(hPipe)
            except:
                pass

    def process_command(self, cmd):
        """Process command from AFSIM, return response string"""
        self.log(f"Processing: {cmd}")

        if cmd == "PING":
            return "PONG"
        elif cmd == "GET_TIME":
            return str(int(time.time() * 1000))
        elif cmd == "STATUS":
            return json.dumps({
                "connected_clients": len(self.clients),
                "server_status": "running",
                "uptime_ms": int((time.time() - self.start_time) * 1000)
            })
        elif cmd.startswith("KILL_CHAIN_CMD:"):
            try:
                payload = cmd[len("KILL_CHAIN_CMD:"):]
                data = json.loads(payload)
                return json.dumps(self.execute_kill_chain_cmd(data))
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"JSON parse failed: {e}"})
        else:
            return json.dumps({"error": f"Unknown command: {cmd}"})

    def execute_kill_chain_cmd(self, data):
        """Execute a kill chain command from AFSIM"""
        cmd_type = data.get("type", "unknown")

        if cmd_type == "TRACK_UPDATE":
            track_id = data.get("track_id")
            lat = data.get("lat")
            lon = data.get("lon")
            alt = data.get("alt")
            self.log(f"Track update: id={track_id} lat={lat} lon={lon} alt={alt}")
            return {"status": "ack", "track_id": track_id}
        elif cmd_type == "SENSOR_REPORT":
            sensor_id = data.get("sensor_id")
            sensor_type = data.get("sensor_type")
            self.log(f"Sensor report: {sensor_id} type={sensor_type}")
            return {"status": "ack", "sensor_id": sensor_id}
        elif cmd_type == "IADS_ALERT":
            alert_level = data.get("alert_level")
            self.log(f"IADS Alert: level={alert_level}")
            return {"status": "ack", "alert_level": alert_level}
        else:
            return {"error": f"Unknown cmd type: {cmd_type}"}

    def run(self):
        """Main server loop - run until stopped"""
        self.running = True
        self.start_time = time.time()

        self.log(f"Starting Kill Chain pipe server on {PIPE_NAME}")
        self.log("Waiting for AFSIM clients...")

        while self.running:
            try:
                hPipe = win32pipe.CreateNamedPipe(
                    PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    BUFFER_SIZE, BUFFER_SIZE, 0, None
                )

                if hPipe == -1 or hPipe is None:
                    self.log("CreateNamedPipe failed (invalid handle)")
                    time.sleep(1)
                    continue

                try:
                    win32pipe.ConnectNamedPipe(hPipe, None)
                except Exception as e:
                    self.log(f"ConnectNamedPipe error: {e}")
                    win32file.CloseHandle(hPipe)
                    continue

                t = threading.Thread(target=self.handle_client, args=(hPipe,), daemon=True)
                t.start()

            except Exception as e:
                self.log(f"Server loop error: {e}")
                time.sleep(1)

        self.log("Server stopped")

    def stop(self):
        self.running = False
        self.logf.close()


def main():
    server = KillChainServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nInterrupted")
        server.stop()


if __name__ == "__main__":
    main()
