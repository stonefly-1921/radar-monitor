"""测试 /api/agent/chat 是否可连接"""
import socket, time

t0 = time.time()
try:
    s = socket.create_connection(("localhost", 8000), timeout=10)
    print(f"Connected in {time.time()-t0:.1f}s")
    # Send HTTP POST request
    body = '{"message":"test","session_id":"sock"}'
    request = f"POST /api/agent/chat HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}"
    s.sendall(request.encode())
    # Wait for response
    s.settimeout(15)
    data = s.recv(4096)
    print(f"Response: {data[:200]}")
    s.close()
except Exception as e:
    print(f"Error: {e}")
