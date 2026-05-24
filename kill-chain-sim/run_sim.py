# Kill-chain-sim simulation runner
import subprocess
import time
import os
import sys

KILL_CHAIN_DIR = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
AFSIM_DIR = r"D:\afsim-2.9.0-win64\bin"
SCENARIO = "kill_chain_np_multi"

track_out = os.path.join(KILL_CHAIN_DIR, "afsim_track_out.txt")
cmd_txt = os.path.join(KILL_CHAIN_DIR, "kill_chain_np_cmd.txt")
ack_txt = os.path.join(KILL_CHAIN_DIR, "kill_chain_np_ack.txt")
evt_out = os.path.join(KILL_CHAIN_DIR, "output", "kill_chain_np_multi.evt")

# Clean slate
for f in [track_out, cmd_txt, ack_txt]:
    if os.path.exists(f):
        os.remove(f)
    with open(f, "w") as fp:
        fp.write("")

print("[CLEAN] Files cleared")

# Start AFSIM in background
os.chdir(os.path.join(KILL_CHAIN_DIR, "src", "sim"))
afsim_proc = subprocess.Popen(
    [os.path.join(AFSIM_DIR, "mission.exe"),
     "--scenario", SCENARIO + ".txt"],
    cwd=os.path.join(KILL_CHAIN_DIR, "src", "sim"),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"[AFSIM] Started PID={afsim_proc.pid}")

# Wait for startup
time.sleep(3)
print("[AFSIM] 3s startup done, starting Python controller")

# Start Python controller in background
python_proc = subprocess.Popen(
    [sys.executable,
     os.path.join(KILL_CHAIN_DIR, "src", "tools", "kill_chain_np_fire_controller.py"),
     "--scenario", SCENARIO],
    cwd=KILL_CHAIN_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"[PYTHON] Started PID={python_proc.pid}")

# Monitor until AFSIM exits (simulation end_time=2min)
print("[MONITOR] Waiting for AFSIM to finish...")
start = time.time()
while True:
    ret = afsim_proc.poll()
    if ret is not None:
        print(f"[AFSIM] Exited with code={ret} after {time.time()-start:.0f}s")
        break
    # check python too
    if python_proc.poll() is not None:
        print(f"[PYTHON] Exited early with code={python_proc.poll()}")
        break
    time.sleep(5)
    elapsed = time.time() - start
    print(f"  alive... {elapsed:.0f}s elapsed", flush=True)
    if elapsed > 300:
        print("[TIMEOUT] 5 min hit, killing processes")
        afsim_proc.kill()
        python_proc.kill()
        break

# Collect results
print("\n[RESULTS]")
for label, path in [("EVT", evt_out), ("TRACK_OUT", track_out)]:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  {label}: {size} bytes")

# Parse EVT if available
if os.path.exists(evt_out) and os.path.getsize(evt_out) > 0:
    print("\n[EVT PARSE]")
    with open(evt_out, "r", encoding="utf-8") as f:
        content = f.read()

    # Count events
    fired = content.count("WEAPON_FIRED")
    missed = content.count("WEAPON_MISSED")
    killed = content.count("WEAPON_HIT")
    termd = content.count("WEAPON_TERMINATED")
    print(f"  WEAPON_FIRED={fired}, WEAPON_MISSED={missed}, WEAPON_HIT={killed}, WEAPON_TERMINATED={termd}")

    # Find fighter2 result
    if "fighter2" in content:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "fighter2" in line:
                print(f"  fighter2 line: {line[:100]}")
else:
    print("  EVT file empty or missing!")

# Python stdout/stderr
print("\n[PYTHON STDOUT]")
py_out, py_err = python_proc.communicate()
if py_out:
    print(py_out.decode("utf-8", errors="replace")[:2000])
if py_err:
    print("STDERR:", py_err.decode("utf-8", errors="replace")[:500])

print("\n[DONE] Simulation run complete")