'''
This code is for the computer that runs Project Cars in Windows.
Basic purpose of this script is to get Pcars data from CREST API and capture the game screen
and resize it, then send it to REDIS server so that the A3C can take the data.
To minimize the elapsed time, each process is divided into threads.

author : Hwanmoo Yong
'''

import redis
import json
import time
from io import BytesIO

import mss
import mss.tools

from PIL import Image
import base64
import numpy as np

from threading import Thread
from multiprocessing import Process

from utils.pcars_stream.src.pcars.stream import PCarsStreamReceiver
from utils.autoController import pCarsAutoController
from utils.autoKiller import pCarsAutoKiller

import http.client
import socket 

from datetime import datetime

''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
print("Local ip",local_ip)
''' Init Redis '''
r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

''' CREST Thread '''
class PCarsListener(object):
    def __init__(self):
        self.data = None

    def handlePacket(self, data):
        # You probably want to do something more exciting here
        # You probably also want to switch on data.packetType
        # See listings in packet.py for packet types and available fields for each
        # print(data._data)
        self.data = data._data
        # print(self.data)

class screen_capture_thread(Thread):        

    def __init__(self, listener):
        self.img = None
        self.listener = listener

        super(screen_capture_thread, self).__init__()

    def run(self):
        try:
            import win32gui
            # import win32ui
            # import win32con

            # Get Focus on project cars window
            windowname = "Project CARS™"
            hwnd = win32gui.FindWindow(None, windowname)
            
            # Get window properties and take screen capture
            l, t, _r, b = win32gui.GetWindowRect(hwnd)

            target_w = 800
            target_h = 600

            margin_w  = int((_r-l-target_w) / 2)

            l = l + margin_w
            _r = _r - margin_w
            b = b - margin_w
            t = t + ((b-t-target_h))
            w = _r - l
            h = b - t

            with mss.mss() as sct:
                # The screen part to capture
                monitor = {'top': t, 'left': l, 'width': w, 'height': h}

                # Grab the data
                msg = self.listener.data
                sct_img = sct.grab(monitor)

            img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')

            buf= BytesIO()
            img = img.resize((200,150), Image.ANTIALIAS)
            img.save(buf, format= 'PNG')

            self.img = base64.b64encode(buf.getvalue()).decode("utf-8")
            result = False
            
            # print(msg)
            if msg is not None:
                if "participants" in msg:
                    if "worldPositionX" in msg["participants"][0]:
                        cur_position_x = msg["participants"][0]["worldPositionX"]
                        cur_position_y = msg["participants"][0]["worldPositionY"]
                        cur_position_z = msg["participants"][0]["worldPositionZ"]
                        
                        if self.listener.data is not False and self.listener.data is not None and self.img is not None:
                            ob = self.listener.data

                            if "gameState" in ob:
                                gameState = ob["gameState"].value
                                raceState = ob["raceState"].value

                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

                                # print("GameState", gameState, "RaceState", raceState)

                                sp = ob["speed"]
                                distance = ob["participants"][0]["currentLapDistance"]
                                print("speed:",sp,"distance:",distance)
    
            exit(0)
            
        except Exception as ex:
            print("Pcars Screen Capture Error :", ex)
            exit(0)
        

if __name__ == '__main__':
    print('Starting Data Sender.. [A3C on Project Cars]')
    ''' 
    Listening Pcars UDP port 
    Make sure to set udp setting in the game option as 1
    '''

    listener = PCarsListener()
    stream = PCarsStreamReceiver()
    stream.addListener(listener)
    stream.start()

    while True:
        # Taking Screen Capture form Pcars
        '''
        스크린샷찍는 process가 0.4초정도 걸리므로
        일단은 귀찮아서 0.08초 단위로 쓰레드를 만들어서 함.
        코드 수정필요
        '''
        # interval = 0.08

        sct = screen_capture_thread(listener)
        sct.daemon = True 
        sct.start()
        sct.join()

        

