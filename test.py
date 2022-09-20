import json
import socket

ip = "192.168.88.122"
data = {"commandId":"checkStatus", "deviceId":"7iCs8gyw", "commandType":"QUERY_DEVICE_INFO"}
data = json.dumps(data)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try: 
    sock.connect((ip, 3333))
    sock.sendall(bytes(data,encoding="utf-8"))
    len = int.from_bytes(sock.recv(4), "big")
    if len > 0 and len < 8192:
        received = sock.recv(len)
        received = received.decode("utf-8")
finally:
    sock.close()

print(json.loads(received))