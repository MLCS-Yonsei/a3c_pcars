from pywinauto.application import Application
from pywinauto.keyboard import SendKeys

import pywinauto

import win32ui
import win32gui
import win32com.client

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

        self.get_focus(0)
        self.status = 'active'

        self.target_ip = 'localhost:8080'
        
        self.connect_arduino()
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
        try:
            self.ard = serial.Serial(port,9600,timeout=5)
        except:
            self.ard = None
            print("No Arduino Found")
            exit(0)
        time.sleep(2)

    def get_focus(self, vpc_idx):
        # Make Pcars window focused
        target_name = "DESKTOP-FOKU7V8의 V" + str(vpc_idx+1) + " - 가상 컴퓨터 연결"
        print(target_name)
        PyCWnd1 = win32ui.FindWindow( None, target_name )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

    def trigger_arduino_esc(self, vpc_idx):
        
        # Make Pcars focused just in case
        self.get_focus(vpc_idx)
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
        self.get_focus()
        # Make Pcars window focused
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "화상 키보드" ))

        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        pywinauto.mouse.move(coords=(x+30, y+0))
        time.sleep(1)
        pywinauto.mouse.press(button='left', coords=(x-5, y+90))
        pywinauto.mouse.click(button='left', coords=(x-5, y+90))
        pywinauto.mouse.press(button='left', coords=(x-5, y+90))
        # pywinauto.mouse.release(button='left', coords=(x+30, y))

    def restart_type_1(self, target_ip, vpc_idx):
        self.trigger_arduino_esc(vpc_idx)

        # time.sleep(0.5)
        # self.get_focus(vpc_idx)
        # # Move to bottom of the menu
        # cmd = '{DOWN}'
        # for i in range(1,11):
        #     SendKeys(cmd)

        # # Restart Btn is located at second bottom of the menu
        # cmd = '{UP}'
        # SendKeys(cmd)

        # # Hit Return
        # cmd = '{ENTER}'
        # SendKeys(cmd)

        # # Wait for confirmation popup shows up
        # time.sleep(0.2)
        # cmd = '{DOWN}'
        # SendKeys(cmd)

        # cmd = '{ENTER}'
        # SendKeys(cmd)

        self.r.hset('pcars_killer',target_ip,"3")

        

        self.ard.close()
        self.connect_arduino()

        return True

    def restart_type_2(self, target_ip, vpc_idx):
        self.r.hset('pcars_killer',target_ip,"4")
        # Wait for session results screen shows up
        # time.sleep(9)
        # self.get_focus(vpc_idx)
        # # Move to bottom of the menu
        # cmd = '{UP}'
        # for i in range(1,6):
        #     SendKeys(cmd)

        # # Restart Btn is located at second bottom of the menu
        # cmd = '{DOWN}'
        # SendKeys(cmd)

        # # Hit Return
        # cmd = '{ENTER}'
        # SendKeys(cmd)

        # # Wait for confirmation popup shows up
        # time.sleep(0.2)
        # cmd = '{DOWN}'
        # SendKeys(cmd)

        # cmd = '{ENTER}'
        # SendKeys(cmd)

        # Wait until game restarts
        # while True:
        #     gameData = send_crest_requset(self.target_ip, "crest-monitor", {})
        #     raceState = gameData["gameStates"]["mRaceState"]

        #     if raceState < 3:
        #         break
        
        return True


if __name__ == '__main__':
    pc = pCarsAutoKiller()
    ips = [
        "192.168.0.72",
        "192.168.0.73"
    ]
    while True:
        for i, local_ip in enumerate(ips):
            message = r.hget('pcars_killer',local_ip)

            if message:
                reset_status = eval(message)

                if reset_status == 1:
                    pc.restart_type_1(local_ip,i)
                elif reset_status == 2:
                    pc.restart_type_2(local_ip,i)

                r.hdel('pcars_killer',local_ip)
    # pc.restart_type_2(ips[0], 0)

            










