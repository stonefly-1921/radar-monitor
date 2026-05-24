# -*- coding: utf-8 -*-
"""MyAgent full loop test using REPL as subprocess with proper stdin handling."""
import os, sys, time, json, subprocess, threading

WORKSPACE = "C:\\Users\\15041\\.openclaw\\workspace\\MyAgent"
PYTHON = "D:\\anaconda3\\python.exe"
API_KEY = open(os.path.join(WORKSPACE, '_apikey.txt')).read().strip()

MINIMAX_BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

def call_minimax(prompt_text, max_tokens=500):
    headers = {
        'Authorization': 'Bearer ' + API_KEY,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': max_tokens
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(MINIMAX_BASE_URL, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('base_resp', {}).get('status_code') != 0:
                return None, result.get('base_resp', {}).get('status_msg', 'unknown')
            content = result.get('content', [])
            text = ''.join([item.get('text', '') for item in content if item.get('type') == 'text'])
            return text, None
    except Exception as e:
        return None, str(e)

# Use subprocess with stdin from a file (simulate interactive input)
# The REPL reads input.txt and waits for enter key - we simulate this with a fake TTY

print("=" * 60)
print("MyAgent Full Loop Test (REPL + MiniMax)")
print("=" * 60)

io_dir = os.path.join(WORKSPACE, 'io')
os.makedirs(io_dir, exist_ok=True)

# Clean up io files
for fname in ['input.txt', 'prompt.txt', 'response.txt', 'final_answer.txt']:
    fpath = os.path.join(io_dir, fname)
    if os.path.exists(fpath):
        os.remove(fpath)

# Step 1: Write task to input.txt
input_file = os.path.join(io_dir, 'input.txt')
with open(input_file, 'w', encoding='utf-8') as f:
    f.write('你好，简单介绍一下自己')
print(f"\n[1] Task written to {input_file}")

# Step 2: Run REPL - pass "anything" via stdin to trigger the file read path
# The REPL checks input.txt first before stdin
env = dict(os.environ)
env['PYTHONIOENCODING'] = 'utf-8'
env['MINIMAX_API_KEY'] = API_KEY

proc = subprocess.Popen(
    [PYTHON, os.path.join(WORKSPACE, 'agent', 'loop_v2.py')],
    cwd=WORKSPACE,
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=1  # Line buffered
)

# Feed empty line + quit after a few seconds
def writer():
    time.sleep(2)
    proc.stdin.write('\n'.encode('utf-8'))
    proc.stdin.flush()
    time.sleep(2)
    proc.stdin.write('quit\n'.encode('utf-8'))
    proc.stdin.flush()

t = threading.Thread(target=writer)
t.start()

# Read output
output_lines = []
for line in iter(proc.stdout.readline, ''):
    if line:
        try:
            decoded = line.decode('utf-8', errors='replace')
        except:
            decoded = line.decode('gbk', errors='replace')
        output_lines.append(decoded.strip())
        print(decoded.rstrip())

proc.wait(timeout=10)
t.join()

# Step 3: Check prompt.txt
prompt_file = os.path.join(io_dir, 'prompt.txt')
if os.path.exists(prompt_file):
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read()
    if prompt.strip():
        print(f"\n[2] Prompt generated! ({len(prompt)} chars)")
        print(f"    Preview: {prompt[:200]}...")

        # Step 4: Call MiniMax
        print("\n[3] Calling MiniMax API...")
        resp_text, error = call_minimax(prompt)
        if error:
            print(f"    Error: {error}")
        else:
            print(f"    Response ({len(resp_text)} chars): {resp_text[:200]}...")

            # Step 5: Write to response.txt and run again
            response_file = os.path.join(io_dir, 'response.txt')
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(resp_text)
            print(f"\n[4] Response written to {response_file}")

            # Run REPL again
            print("\n[5] Running REPL again...")
            proc2 = subprocess.Popen(
                [PYTHON, os.path.join(WORKSPACE, 'agent', 'loop_v2.py')],
                cwd=WORKSPACE,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1
            )
            def writer2():
                time.sleep(2)
                proc2.stdin.write('quit\n'.encode('utf-8'))
                proc2.stdin.flush()
            t2 = threading.Thread(target=writer2)
            t2.start()
            for line in iter(proc2.stdout.readline, ''):
                if line:
                    try:
                        decoded = line.decode('utf-8', errors='replace')
                    except:
                        decoded = line.decode('gbk', errors='replace')
                    print(decoded.rstrip())
            proc2.wait(timeout=10)
            t2.join()

            # Check final answer
            final_file = os.path.join(io_dir, 'final_answer.txt')
            if os.path.exists(final_file):
                with open(final_file, 'r', encoding='utf-8') as f:
                    final = f.read()
                print(f"\n[6] Final answer: {final[:300]}...")
    else:
        print("\n[2] Prompt file is empty")
else:
    print("\n[2] No prompt file generated")

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)