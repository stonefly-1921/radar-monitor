import subprocess, time, os, sys, re
from PIL import ImageGrab

KILL_CHAIN_DIR = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
AFSIM_BIN = r"D:\afsim-2.9.0-win64\bin\mission.exe"

# Clean
for f in ["afsim_track_out.txt", "kill_chain_np_cmd.txt", "kill_chain_np_ack.txt"]:
    open(os.path.join(KILL_CHAIN_DIR, f), "w").close()

log_path = os.path.join(KILL_CHAIN_DIR, "run_afsim.log")
err_path = os.path.join(KILL_CHAIN_DIR, "run_afsim.err")
p = subprocess.Popen(
    [AFSIM_BIN, "src/sim/kill_chain_np_multi.txt"],
    cwd=KILL_CHAIN_DIR,
    stdout=open(log_path, "w"),
    stderr=open(err_path, "w"),
)
print(f"AFSIM PID={p.pid}")
time.sleep(5)  # Let AFSIM init

# Start fire controller
fire_proc = subprocess.Popen(
    [sys.executable,
     os.path.join(KILL_CHAIN_DIR, "src", "tools", "kill_chain_np_fire_controller.py"),
     "--scenario", "src/sim/kill_chain_np_multi.txt"],
    cwd=KILL_CHAIN_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"Fire controller PID={fire_proc.pid}")

# Wait for WEAPON_FIRED (max 150s from now)
evt_path = os.path.join(KILL_CHAIN_DIR, "output", "kill_chain_np_multi.evt")
t0 = time.time()
shot = False
while time.time() - t0 < 150 and p.poll() is None:
    if os.path.exists(evt_path) and os.path.getsize(evt_path) > 50:
        with open(evt_path) as f:
            c = f.read()
        if "WEAPON_FIRED" in c and not shot:
            print("WEAPON_FIRED! Screenshot in 2s...")
            time.sleep(2)
            img = ImageGrab.grab()
            p2 = os.path.join(KILL_CHAIN_DIR, "output", "weapon_fired.png")
            img.save(p2)
            print(f"Saved: {p2}")
            shot = True
            # Wait a few more seconds for missile in flight
            time.sleep(5)
            img2 = ImageGrab.grab()
            p3 = os.path.join(KILL_CHAIN_DIR, "output", "weapon_inflight.png")
            img2.save(p3)
            print(f"Saved: {p3}")
            break
    time.sleep(0.5)

p.wait()
fire_proc.kill()
print("Done")

# Print results
if os.path.exists(evt_path):
    with open(evt_path) as f:
        content = f.read()
    print(f"EVT: FIRED={content.count('WEAPON_FIRED')} MISS={content.count('WEAPON_MISSED')} HIT={content.count('WEAPON_HIT')}")
    print("\nEVT content:")
    print(content[:1000])