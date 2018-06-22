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

import win32gui
import win32ui
import win32con

from PIL import Image
import numpy as np

from threading import Thread

from pcars_stream.src.pcars.stream import PCarsStreamReceiver

import http.client
import socket 
''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]

''' Init Redis '''
r = redis.StrictRedis(host='lab.hwanmoo.kr', port=6379, db=1)

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

class screen_capture_thread(Thread):        

    def __init__(self):
        self.img = None
        super(screen_capture_thread, self).__init__()

    def run(self):
        # Get Focus on project cars window
        windowname = "Project CARS™"
        hwnd = win32gui.FindWindow(None, windowname)
        
        # Get window properties and take screen capture
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        w = r - l
        h = b - t
        wDC = win32gui.GetWindowDC(hwnd)
        dcObj=win32ui.CreateDCFromHandle(wDC)
        cDC=dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, w, h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0,0),(w, h) , dcObj, (0,0), win32con.SRCCOPY)
        # dataBitMap.SaveBitmapFile(cDC, bmpfilenamename)

        bmpinfo = dataBitMap.GetInfo()
        bmpstr = dataBitMap.GetBitmapBits(True)

        im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

        self.img = np.array2string(np.array(im), separator=',')

        # Free Resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())
        


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
        sct = screen_capture_thread()
        sct.daemon = True 
        sct.start()

        sct.join()
        
        # Set game_data from pcars udp listener after taking screen capturing
        if listener.data is not False and sct.img is not None:
            result = {'game_data':listener.data,'image_data':sct.img}
        else:
            result = False

        r.hdel('pcars_data',local_ip)
        r.hset('pcars_data',local_ip,result)
        

        

