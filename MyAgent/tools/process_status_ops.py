# -*- coding: utf-8 -*-
"""
Process status tool - list running processes with name, PID, and memory usage.
Windows implementation using tasklist command (no psutil needed).
"""
import subprocess
import csv
import io
import sys


class ProcessStatusTool(object):
    """Tool to get current process list with name, PID, and memory usage."""

    name = "process_status"
    description = u"获取当前进程列表（进程名、PID、内存占用）"
    parameters = []

    def execute(self, **kwargs):
        """
        Execute the tool to get process list.

        Returns:
            list: List of dicts with keys: name (str), pid (int), memory_mb (float)
        """
        try:
            if sys.platform == "win32":
                # Use tasklist for Windows - CSV format, no header
                # Output: "Image Name","PID","Session Name","Session#","Mem Usage"
                cmd = ["tasklist", "/FO", "CSV", "/NH"]
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                if proc.returncode != 0:
                    return {
                        "success": False,
                        "error": "Failed to run tasklist: " + proc.stderr
                    }
                return self._parse_csv_output(proc.stdout)
            else:
                # Cross-platform fallback: use ps command
                return self._parse_ps_output()
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_csv_output(self, output):
        """Parse tasklist CSV output into list of process dicts."""
        processes = []
        reader = csv.reader(io.StringIO(output))
        for row in reader:
            if len(row) < 5:
                continue
            # Row format: "Image Name","PID","Session Name","Session#","Mem Usage"
            name = row[0].strip('"')
            try:
                pid = int(row[1])
            except ValueError:
                continue
            # Memory in KB - convert to MB
            mem_str = row[4].strip().replace(",", "").replace(' K', "").replace('K', "")
            try:
                memory_kb = int(mem_str)
                memory_mb = round(memory_kb / 1024.0, 2)
            except ValueError:
                memory_mb = 0.0
            processes.append({
                "name": name,
                "pid": pid,
                "memory_mb": memory_mb
            })
        return processes

    def _parse_ps_output(self):
        """Cross-platform fallback using ps command."""
        try:
            proc = subprocess.run(
                ["ps", "aux"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            processes = []
            lines = proc.stdout.split("\n")
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 11:
                    try:
                        pid = int(parts[1])
                        # RSS is in KB, convert to MB
                        rss_kb = float(parts[5])
                        memory_mb = round(rss_kb / 1024.0, 2)
                        name = parts[10]
                        processes.append({
                            "name": name,
                            "pid": pid,
                            "memory_mb": memory_mb
                        })
                    except (ValueError, IndexError):
                        continue
            return processes
        except Exception:
            return []

    def validate(self, params):
        """Validate parameters (none required)."""
        return True, None

    def get_spec(self):
        """Get tool specification."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


def register_tools(registry):
    """Register process status tool."""
    registry.register(ProcessStatusTool())