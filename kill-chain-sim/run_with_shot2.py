import subprocess, time, os, sys, re
from PIL import ImageGrab

KILL_CHAIN_DIR = r"C:\Users\15041\.openclaw\workspace\kill-chain-sim"
AFSIM_BIN = r"D:\afsim-2.9.0-win64\bin\mission.exe"

# Clean
for f in ["afsim_track_out.txt", "kill_chain_np_cmd.txt", "kill_chain_np_ack.txt"]:
    open(os.path.join(KILL_CHAIN_DIR, f), "w").close()

# Start AFSIM with correct CWD
p = subprocess.Popen(
    [AFSIM_BIN, "src/sim/kill_chain_np_multi.txt"],
    cwd=KILL_CHAIN_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"AFSIM PID={p.pid}")
time.sleep(5)
ret = p.poll()
print(f"After 5s: ret={ret}")
if ret is not None:
    out, err = p.communicate()
    print("STDOUT:", out[:800])
    print("STDERR:", err[:800])
else:
    print("AFSIM still running, taking screenshot...")
    img = ImageGrab.grab()
    out_path = os.path.join(KILL_CHAIN_DIR, "output", "afsim_running.png")
    img.save(out_path)
    print(f"Screenshot: {out_path}, {img.size}")

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

    # Wait for WEAPON_FIRED
    evt_path = os.path.join(KILL_CHAIN_DIR, "output", "kill_chain_np_multi.evt")
    t0 = time.time()
    shot = False
    while time.time() - t0 < 120 and p.poll() is None:
        if os.path.exists(evt_path) and os.path.getsize(evt_path) > 50:
            with open(evt_path) as f:
                c = f.read()
            if "WEAPON_FIRED" in c and not shot:
                print("WEAPON_FIRED detected! Screenshot in 2s...")
                time.sleep(2)
                img = ImageGrab.grab()
                p2 = os.path.join(KILL_CHAIN_DIR, "output", "weapon_fired.png")
                img.save(p2)
                print(f"Saved: {p2}")
                shot = True
                break
        time.sleep(0.5)

    # Wait for AFSIM
    p.wait()
    fire_proc.kill()
    print("Done")