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

from autoController import pCarsAutoController

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

        self.local_ip = 'localhost:8080'
        
        self.connect_arduino()
        self.prevLapDistance = 0

        self.prev_sp = None

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
            # gameData = send_crest_requset(self.local_ip, "crest-monitor", {})
            # gameState = gameData["gameStates"]["mRaceState"]

            # if gameState == 3:
            #     break

        return True

    def trigger_arduino_enter(self):
        
        # Make Pcars focused just in case
        self.get_focus()
        while True:
            # Send Signal
            self.ard.write(b"enter")
            time.sleep(0.3)
            msg = self.ard.readline()

            # Finish if sec signal succeed
            if msg == b'enter\r\n':
                break

        return True
    
    
    def press_vkey(self,px,py):
        self.get_focus()
        # Make Pcars window focused
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "화상 키보드" ))

        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        # time.sleep(1)
        t1 = datetime.datetime.now()
        pywinauto.mouse.press(button='left', coords=(x+px, y+py))
        # pywinauto.mouse.click(button='left', coords=(x+5, y+90))
        # pywinauto.mouse.press(button='left', coords=(x+5, y+90))
        pywinauto.mouse.release(button='left', coords=(x+px, y))
        t2 = datetime.datetime.now()

        # print(t2-t1)

    def trigger_virtual_esc(self):
        px = 30
        py = 150

        self.press_vkey(px,py)


    def trigger_virtual_enter(self):
        px = 550
        py = 380

        self.press_vkey(px,py)

    def send_enter(self):
        cmd = '{ENTER}'
        SendKeys(cmd)

    def restart_type_1(self):
        self.trigger_arduino_esc()

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
        #     gameData = send_crest_requset(self.local_ip, "crest-monitor", {})
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
        pac = pCarsAutoController()
        pac.move_steer(0)
        pac.brakeOff()
        pac.accOff()
        cnt = 0
        while True:
            kill_message = r.hget('pcars_killer'+local_ip,local_ip)
            if kill_message:
                km = eval(kill_message)
                if km != 4:
                    break
                    
            message = self.r.hget('pcars_data'+local_ip,local_ip)

            if message:
                                            
                self.r.hdel('pcars_data'+local_ip,local_ip)
                message = message.decode("utf-8")
                message = message.replace('<','\'<')
                message = message.replace('>','>\'')

                msg = eval(message)
                ob = msg['game_data']

                if "speed" in ob:
                    # cnt += 1
                    # if cnt > 10:
                    #     break

                    sp = ob["speed"]

                    if self.prev_sp is None:
                        self.prev_sp = sp
                        self.prev_action = 'brake'
                        pac.accOff()
                        pac.brakeOn()
                        
                    elif self.prev_sp > sp:
                        self.prev_sp = sp

                        if self.prev_action == 'brake':
                            pac.accOff()
                            pac.brakeOn()
                        else:
                            pac.brakeOff()
                            pac.accOn()

                    elif self.prev_sp < sp:
                        self.prev_sp = sp

                        if self.prev_action == 'brake':
                            pac.brakeOff()
                            pac.accOn()
                            
                            self.prev_action = 'acc'
                        else:
                            pac.accOff()
                            pac.brakeOn()

                            self.prev_action = 'brake'

                    time.sleep(0.5)
                    pac.brakeOff()
                    pac.accOff()
                    # self.trigger_virtual_enter()
                    # self.trigger_arduino_enter()

                    if sp < 0.2:
                        # self.trigger_virtual_enter()
                        print("speed almost 0")
                        self.trigger_arduino_enter()
                        break

        return True

if __name__ == '__main__':
    pc = pCarsAutoKiller()

    while True:
        message = r.hget('pcars_killer'+local_ip,local_ip)
        
        if message:
            reset_status = eval(message)
            print(reset_status)
            if reset_status == 1:
                pc.restart_type_1()
                del_stat = True
            elif reset_status == 2:
                pc.restart_type_2()
                del_stat = True
            elif reset_status == 3:
                pc.restart_type_3()
                del_stat = True
            elif reset_status == 4:
                pc.restart_type_4()
                del_stat = False
                r.hset('pcars_killer'+local_ip,local_ip,"0")
            elif reset_status == 0:
                del_stat = False
            else:
                del_stat = True

            if del_stat:
                r.hdel('pcars_killer'+local_ip,local_ip)
            
    # print("V esc")
    # time.sleep(3)
    
    # pc.restart_type_4()

                
            

            










