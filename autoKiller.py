from pywinauto.application import Application
from pywinauto.keyboard import SendKeys
import win32ui

import serial
import serial.tools.list_ports

# from utils import send_crest_requset

import subprocess 
import multiprocessing as mp
from threading import Thread
from multiprocessing import Pool
from queue import Empty

import time
import datetime
import os
import signal
import redis
import socket

''' Init Redis '''
r = redis.StrictRedis(host='lab.hwanmoo.kr', port=6379, db=1)

''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]


class pCarsAutoKiller(mp.Process):
    def __init__(self):
        super(pCarsAutoKiller,self).__init__()
        #self.queue = que

        self.get_focus()
        self.status = 'active'

        self.target_ip = 'localhost:8080'
        
        self.connect_arduino()
        self.prevLapDistance = 0

        self.run()

    def connect_arduino(self):
        # Scan for arduino ports
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "Arduino" in p[1]:
                port = p[0]
                break

        self.ard = serial.Serial(port,9600,timeout=5)
        time.sleep(2)

    def get_focus(self):
        # Make Pcars window focused
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

    def trigger_esc(self):
        
        # Make Pcars focused just in case
        self.get_focus()
        while True:
            # Send Signal
            self.ard.write(b"esc")
            time.sleep(0.3)
            msg = self.ard.readline()

            # Finish if sec signal succeed
            if msg == b'esc\r\n':
                break

            # check if menu pops up
            # gameData = send_crest_requset(self.target_ip, "crest-monitor", {})
            # gameState = gameData["gameStates"]["mRaceState"]

            # if gameState == 3:
            #     break

        
        return True

    def restart_type_1(self):
        self.trigger_esc()

        time.sleep(0.5)
        self.get_focus()
        # Move to bottom of the menu
        cmd = '{DOWN}'
        for i in range(1,11):
            SendKeys(cmd)

        # Restart Btn is located at second bottom of the menu
        cmd = '{UP}'
        SendKeys(cmd)

        # Hit Return
        cmd = '{ENTER}'
        SendKeys(cmd)

        # Wait for confirmation popup shows up
        time.sleep(0.2)
        cmd = '{DOWN}'
        SendKeys(cmd)

        cmd = '{ENTER}'
        SendKeys(cmd)

        # Wait until game restarts
        # while True:
        #     gameData = send_crest_requset(self.target_ip, "crest-monitor", {})
        #     gameState = gameData["gameStates"]["mRaceState"]

        #     if gameState == 2:
        #         break

        self.ard.close()
        self.connect_arduino()
        return True

    def restart_type_2(self):
        # Wait for session results screen shows up
        time.sleep(9)
        self.get_focus()
        # Move to bottom of the menu
        cmd = '{UP}'
        for i in range(1,6):
            SendKeys(cmd)

        # Restart Btn is located at second bottom of the menu
        cmd = '{DOWN}'
        SendKeys(cmd)

        # Hit Return
        cmd = '{ENTER}'
        SendKeys(cmd)

        # Wait for confirmation popup shows up
        time.sleep(0.2)
        cmd = '{DOWN}'
        SendKeys(cmd)

        cmd = '{ENTER}'
        SendKeys(cmd)

        # Wait until game restarts
        # while True:
        #     gameData = send_crest_requset(self.target_ip, "crest-monitor", {})
        #     raceState = gameData["gameStates"]["mRaceState"]

        #     if raceState < 3:
        #         break
        
        return True
    '''
    def run(self):
        while True:
            if self.status == 'active':
                gameData = send_crest_requset(self.target_ip, "crest-monitor", {})

                # parse Game Data
                gameState = gameData["gameStates"]["mGameState"]

                if gameState > 1:
                    raceState = gameData["gameStates"]["mRaceState"]
                    crashState = gameData["carDamage"]["mCrashState"]
                    tireTerrain = gameData["wheelsAndTyres"]["mTerrain"]
                    
                    lapLength = gameData["eventInformation"]["mTrackLength"] # 랩 길이
                    
                    egoInfo = gameData["participants"]["mParticipantInfo"][0]
                    lapCompleted = egoInfo["mLapsCompleted"]
                    currentLapDistance = egoInfo["mCurrentLapDistance"] + lapLength * lapCompleted
                    
                    # Case
                    if raceState == 3:
                        print(1)
                        self.restart_type_2()
                    elif crashState > 1:
                        print(2)
                        self.restart_type_1()
                    elif self.prevLapDistance != 0 and currentLapDistance != 0 and currentLapDistance <= self.prevLapDistance:
                        print(3)
                        self.restart_type_1()
                    elif tireTerrain.count(0) != 4:
                        print(4)
                        self.restart_type_1()

                    self.prevLapDistance = currentLapDistance
    '''
if __name__ == '__main__':
    pc = pCarsAutoKiller()
    while True:
        message = r.hget('pcars_killer',local_ip)

        if message:
            reset_status = eval(message)

            if reset_status == 1:
                pc.restart_type_1()
            elif reset_status == 2:
                pc.restart_type_2()

            r.hdel('pcars_killer',local_ip)

            










