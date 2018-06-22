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

from threading import Thread
import socket 
''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]

''' Init Redis '''
r = redis.StrictRedis(host='lab.hwanmoo.kr', port=6379, db=1)

''' CREST Thread '''
class crest_thread(Thread):        

    def __init__(self):
        self.crest_data = None
        super(crest_thread, self).__init__()

    def send_crest_requset(self, url, flag, option):
        conn = http.client.HTTPConnection(url, timeout=1)
        try:
            conn.request("GET", "/crest/v1/api")

            res = conn.getresponse()

            data = json.loads(res.read().decode('utf8', "ignore").replace("'", '"'))

            if data["gameStates"]["mGameState"] > 1:
                if flag == 'crest-monitor':
                    return data
        except Exception as e:
            # print("CREST_ERROR on send_crest_request:", e)
            return False

    def run(self):
        try:
            ''' Try 8080 port to get crest data '''
            crest_data = self.send_crest_requset('localhost:8080', "crest-monitor", {})
            gameState = crest_data['gameStates']['mGameState']

            if gameState > 1 and 'participants' in crest_data:
                if 'mParticipantInfo' in crest_data["participants"]:
                    # 게임 플레이중
                    return crest_data
            else:
                return False

        except Exception as e:
            try:
                ''' Try 9090 port to get crest data '''
                crest_data = self.send_crest_requset('localhost:9090', "crest-monitor", {})
                gameState = crest_data['gameStates']['mGameState']

                if gameState > 1 and 'participants' in crest_data:
                    if 'mParticipantInfo' in crest_data["participants"]:
                        # 게임 플레이중
                        return crest_data
            except Exception as e:
                return False



class screen_capture_thread(Thread):        

    def __init__(self):
        self.img = None
        super(screen_capture_thread, self).__init__()

    def run(self):
        # Get Focus on project cars window
        windowname = "Project CARS™"
        hwnd = win32gui.FindWindow(None, windowname)
        
        # Get window properties and take screen capture
        w = 600
        h = 480
        wDC = win32gui.GetWindowDC(hwnd)
        dcObj=win32ui.CreateDCFromHandle(wDC)
        cDC=dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, w, h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0,0),(w, h) , dcObj, (0,0), win32con.SRCCOPY)
        # dataBitMap.SaveBitmapFile(cDC, bmpfilenamename)
        self.img = cDC
        print("dataBitMap",dataBitMap)
        print("cDC",cDC)
        exit(0)
        # Free Resources
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())


if __name__ == '__main__':
    print('Starting Data Sender.. [A3C on Project Cars]')
    while True:
        # Getting Data from CREST API
        ct = crest_thread()
        ct.daemon = True 
        ct.start()

        # Taking Screen Capture form Pcars
        sct = screen_capture_thread()
        sct.daemon = True 
        sct.start()

        ct.join()
        sct.join()

        if ct.crest_data is not False and sct.img is not None:
            result = {game_data:crest_data,image_data:img}
        else:
            result = False
        r.hdel('pcars_data',local_ip)
        r.hset('pcars_data',local_ip,result)
        

        

