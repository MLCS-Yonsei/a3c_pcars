from pywinauto.application import Application
from pywinauto.keyboard import SendKeys
import win32ui
import win32gui

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
r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]


class pCarsAutoKiller(mp.Process):
    def __init__(self):
        super(pCarsAutoKiller,self).__init__()
        #self.queue = que

        self.get_focus()
        self.status = 'active'

        self.target_ip = 'localhost:8080'
        
        # self.connect_arduino()
        self.prevLapDistance = 0

        ''' Getting Local IP of this Computer '''
        self.local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
        print("Local IP for AutoKiller: ",self.local_ip)
        ''' Init Redis '''
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
        print("Redis connected for AutoKiller: ",self.r)

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

    def trigger_arduino_esc(self):
        
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

    def trigger_virtual_esc(self):
        # Make Pcars window focused
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "화상 키보드" ))
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        
        # pywinauto.mouse.click(button='left', coords=(x+30, y+160))
        pywinauto.mouse.press(button='left', coords=(x+30, y+160))
        pywinauto.mouse.release(button='left', coords=(x+30, y))

    def restart_type_1(self):
        self.trigger_virtual_esc()

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
    def run(self):
        while True:
            message = self.r.hget('pcars_killer',self.local_ip)

            if message:
                reset_status = eval(message)

                if reset_status == 1:
                    self.restart_type_1()
                elif reset_status == 2:
                    self.restart_type_2()

                self.r.hdel('pcars_killer',self.local_ip)

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

            










