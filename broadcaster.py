from socket import *
import json

svrsock = socket(AF_INET, SOCK_DGRAM)
svrsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
svrsock.bind(('', 54545))               #로컬호스트에 5001포트로 바인딩

while True:
    s, addr = svrsock.recvfrom(1024)

    if s == b'Connect':
        svrsock.sendto('OK'.encode(),addr)
    else:
        control = json.loads(s.decode())
        print(control['steer'])


