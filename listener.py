import time
import json

from socket import *
csock = socket(AF_INET, SOCK_DGRAM)
csock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
csock.bind(('', 6001))

status = False

i = 0
while True:
    time.sleep(0.1)
    if status == False:
        csock.sendto('Connect'.encode(), ('192.168.0.49',54545)) # 대상 서버 , 목적지 포트
        s, addr = csock.recvfrom(4096)
        print('Connected!')
        status = True
    else:
        print(i)
        i = i + 1

        n = i / 20
        if n < 0.3:
            controlState = {
                'acc': True,
                'brake': False,
                'steer': n
            }
        elif n >= 0.3 and n < 0.7:
            controlState = {
                'acc': False,
                'brake': True,
                'steer': -n
            }
        else:
            controlState = {
                'acc': True,
                'brake': False,
                'steer': n
            }
        
        json_str = json.dumps(controlState)

        csock.sendto(json_str.encode(), ('192.168.0.49',54545)) # 대상 서버 , 목적지 포트
