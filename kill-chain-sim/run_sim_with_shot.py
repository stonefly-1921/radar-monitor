# Screenshot-capable simulation runner
import subprocess, time, os, sys, re
import mss

KILL_CHAIN_DIR = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
AFSIM_BIN = r"D:\afsim-2.9.0-win64\bin\mission.exe"
SCENARIO = "src/sim/kill_chain_np_multi.txt"

track_out = os.path.join(KILL_CHAIN_DIR, "afsim_track_out.txt")
cmd_txt = os.path.join(KILL_CHAIN_DIR, "kill_chain_np_cmd.txt")
ack_txt = os.path.join(KILL_CHAIN_DIR, "kill_chain_np_ack.txt")
evt_out = os.path.join(KILL_CHAIN_DIR, "output", "kill_chain_np_multi.evt")

# Clean slate
for f in [track_out, cmd_txt, ack_txt]:
    if os.path.exists(f):
        os.remove(f)
    open(f, "w").close()

print("[CLEAN] Files cleared")

# Start AFSIM in background
os.chdir(KILL_CHAIN_DIR)
afsim_proc = subprocess.Popen(
    [AFSIM_BIN, SCENARIO],
    cwd=KILL_CHAIN_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"[AFSIM] Started PID={afsim_proc.pid}")
time.sleep(3)

# Start Python controller
python_proc = subprocess.Popen(
    [sys.executable,
     os.path.join(KILL_CHAIN_DIR, "src", "tools", "kill_chain_np_fire_controller.py"),
     "--scenario", SCENARIO],
    cwd=KILL_CHAIN_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"[PYTHON] Started PID={python_proc.pid}")

# Wait for weapon fired event in EVT
print("[MONITOR] Waiting for WEAPON_FIRED event...")
shot_taken = False
start = time.time()
weapon_fired_time = None

while time.time() - start < 300:
    ret = afsim_proc.poll()
    if ret is not None:
        print(f"[AFSIM] Exited code={ret}")
        break

    # Check EVT for weapon fired
    if os.path.exists(evt_out) and os.path.getsize(evt_out) > 100:
        with open(evt_out, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "WEAPON_FIRED" in content and not shot_taken:
            matches = re.findall(r"(\d+:\d+:\d+\.\d+).*?WEAPON_FIRED", content)
            if matches:
                print(f"[TRIGGER!] WEAPON_FIRED detected at {matches[0]}")
                time.sleep(1)  # Let window render fully
                # Take screenshot
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    img_path = os.path.join(KILL_CHAIN_DIR, "output", "weapon_fired_screenshot.png")
                    sct.to_png(img_path, screenshot)
                print(f"[SCREENSHOT] Saved: {img_path}")
                shot_taken = True
                # Also capture a few more seconds later for missile in flight
                time.sleep(3)
                with mss.mss() as sct:
                    screenshot2 = sct.grab(sct.monitors[1])
                    img_path2 = os.path.join(KILL_CHAIN_DIR, "output", "weapon_inflight_screenshot.png")
                    sct.to_png(img_path2, screenshot2)
                print(f"[SCREENSHOT2] Saved: {img_path2}")
                break

    time.sleep(0.5)

# Wait for AFSIM to finish
print("[MONITOR] Waiting for AFSIM to finish...")
while afsim_proc.poll() is None and time.time() - start < 300:
    time.sleep(5)
    print(f"  alive... {time.time()-start:.0f}s")

afsim_proc.kill()
python_proc.kill()
print("[DONE]")