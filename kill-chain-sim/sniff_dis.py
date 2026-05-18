import socket, struct, sys, time
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 3225))
mreq = struct.pack('4s4s', socket.inet_aton('224.2.25.55'), socket.inet_aton('0.0.0.0'))
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
sock.settimeout(35.0)
print(f'Listening on 224.2.25.55:3225...')
sys.stdout.flush()
while 1:
    try:
        data, addr = sock.recvfrom(8192)
        t = data[2]
        print(f't={t} type={data[2]} len={len(data)} from {addr}')
        sys.stdout.flush()
    except socket.timeout:
        print('timeout - no PDUs received')
        break
    except Exception as e:
        print(f'error: {e}')
        break