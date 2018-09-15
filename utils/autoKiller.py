from pywinauto.application import Application
from pywinauto.keyboard import SendKeys

import pywinauto

import win32ui
import win32gui
import win32com.client

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

from utils.autoController import pCarsAutoController

from utils.keys import Keys

class pCarsAutoKiller(mp.Process):
    def __init__(self):
        super(pCarsAutoKiller,self).__init__()
        #self.queue = que

        self.get_focus()
        self.status = 'active'

        self.prevLapDistance = 0

        self.keys = Keys()

        ''' Getting Local IP of this Computer '''
        self.local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
        print("Local IP for AutoKiller: ",self.local_ip)
        ''' Init Redis '''
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
        print("Redis connected for AutoKiller: ",self.r)

        self.pac = pCarsAutoController()

    def get_focus(self):
        # Make Pcars window focused
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()
  
    def press_vkey(self,key):
        self.get_focus()

        self.keys.directKey(key)
        sleep(0.04)
        self.keys.directKey(key, keys.key_release)

    def trigger_virtual_esc(self):
        px = 30
        py = 150

        self.press_vkey("ESC")


    def trigger_virtual_enter(self):
        px = 550
        py = 380

        self.press_vkey("RETURN")
        print("RETURN PRESSED")

    def send_enter(self):
        cmd = '{ENTER}'
        SendKeys(cmd)

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

        self.trigger_virtual_esc()

        return True

    def restart_type_3(self):
        time.sleep(7)

        self.get_focus()
        cmd = '{UP}'
        for i in range(0,3):
            SendKeys(cmd)

        cmd = '{DOWN}'
        SendKeys(cmd)

        # Hit Return
        cmd = '{ENTER}'
        SendKeys(cmd)

        time.sleep(0.2)
        cmd = '{DOWN}'
        SendKeys(cmd)

        cmd = '{ENTER}'
        SendKeys(cmd)

        return True

    def restart_type_4(self):
        print("Rst type 4 start")
        pac = self.pac

        pac.move_steer(0)
        pac.brakeOff()
        pac.accOff()
        pac.handBrakeOn()
        print("Loop start")
        while True:
            message = self.r.hget('pcars_data'+self.local_ip,self.local_ip)

            if message:
                msg = eval(message)
                ob = msg['game_data']

                if "speed" in ob:
                    sp = ob["speed"]
                    if sp < 0.1:
                        self.trigger_virtual_enter()
                        pac.handBrakeOff()   
                        print("Loop escaped")
                        break
                                   
        
        return True





