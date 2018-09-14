from pywinauto.application import Application
import pywinauto

import win32ui
import win32gui
import win32com.client

import serial
import serial.tools.list_ports

# from utils import send_crest_requset
import multiprocessing as mp
import time
import json

import redis
import socket

class pCarsAutoController(mp.Process):
    def __init__(self):
        super(pCarsAutoController,self).__init__()

        self.get_focus()
        self.status = 'active'

        self.controlState = {
            'acc': False,
            'brake': False,
            'steer': 0
        }

        ''' Getting Local IP of this Computer '''
        self.local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
        print("Local IP for AutoController: ",self.local_ip)
        ''' Init Redis '''
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
        print("Redis connected for AutoController: ",self.r)

    def get_focus(self):
        # Make Pcars window focused
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

        return PyCWnd1

    def action_parser(self, this_action):
        if this_action['0'] == True:
            self.brakeOff()
            self.move_steer(-1)
            self.accOn()
        elif this_action['1'] == True:
            self.brakeOff()
            self.move_steer(-1)
            self.accOff()
        elif this_action['2'] == True:
            self.brakeOff()
            self.move_steer(-0.75)
            self.accOn()
        elif this_action['3'] == True:
            self.brakeOff()
            self.move_steer(-0.75)
            self.accOff()
        elif this_action['4'] == True:
            self.brakeOff()
            self.move_steer(-0.5)
            self.accOn()
        elif this_action['5'] == True:
            self.brakeOff()
            self.move_steer(-0.5)
            self.accOff()
        elif this_action['6'] == True:
            self.brakeOff()
            self.move_steer(-0.35)
            self.accOn()
        elif this_action['7'] == True:
            self.brakeOff()
            self.move_steer(-0.35)
            self.accOff()
        elif this_action['8'] == True:
            self.brakeOff()
            self.move_steer(-0.2)
            self.accOn()
        elif this_action['9'] == True:
            self.brakeOff()
            self.move_steer(-0.2)
            self.accOff()
        elif this_action['10'] == True:
            self.brakeOff()
            self.move_steer(-0.1)
            self.accOn()
        elif this_action['11'] == True:
            self.brakeOff()
            self.move_steer(-0.1)
            self.accOff()
        elif this_action['12'] == True:
            self.brakeOff()
            self.move_steer(0)
            self.accOn()
        elif this_action['13'] == True:
            self.brakeOff()
            self.move_steer(0)
            self.accOff()
        elif this_action['14'] == True:
            self.brakeOff()
            self.move_steer(0.1)
            self.accOn()
        elif this_action['15'] == True:
            self.brakeOff()
            self.move_steer(0.1)
            self.accOff()
        elif this_action['16'] == True:
            self.brakeOff()
            self.move_steer(0.2)
            self.accOn()
        elif this_action['17'] == True:
            self.brakeOff()
            self.move_steer(0.2)
            self.accOff()
        elif this_action['18'] == True:
            self.brakeOff()
            self.move_steer(0.35)
            self.accOn()
        elif this_action['19'] == True:
            self.brakeOff()
            self.move_steer(0.35)
            self.accOff()
        elif this_action['20'] == True:
            self.brakeOff()
            self.move_steer(0.5)
            self.accOn()
        elif this_action['21'] == True:
            self.brakeOff()
            self.move_steer(0.5)
            self.accOff()
        elif this_action['22'] == True:
            self.brakeOff()
            self.move_steer(0.75)
            self.accOn()
        elif this_action['23'] == True:
            self.brakeOff()
            self.move_steer(0.75)
            self.accOff()
        elif this_action['24'] == True:
            self.brakeOff()
            self.move_steer(1)
            self.accOn()
        elif this_action['25'] == True:
            self.brakeOff()
            self.move_steer(1)
            self.accOff()
        
        elif this_action['26'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(-1)
        elif this_action['27'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(-0.5)
        elif this_action['28'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(-0.15)
        elif this_action['29'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(0)
        elif this_action['30'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(0.15)
        elif this_action['31'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(0.5)
        elif this_action['32'] == True:
            self.accOff()
            self.brakeOn()
            self.move_steer(1)

            

    def steer_converter(self, n):
        # if n > 1:
        #     n = 1
        # elif n < -1:
        #     n = -1

        self.get_focus()
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "Project CARS™" ))
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        zero = [x + int(w/2), y + int(15 * int(h) / 16)]

        w = w-16 # Margin for window border
        d = int(w/2 * n)
        print("Steering:", n, "ACC", self.controlState['acc'], "Brake", self.controlState['brake'])
        t = [zero[0] + d, zero[1]]

        return t

    def move_steer(self, n):
        self.controlState['steer'] = n
        t = self.steer_converter(n)
        pywinauto.mouse.move(coords=(t[0], t[1]))

    def accOn(self):
        self.controlState['acc'] = True
        t = self.steer_converter(self.controlState['steer'])
        pywinauto.mouse.press(button='left', coords=(t[0], t[1]))

    def accOff(self):
        self.controlState['acc'] = False
        t = self.steer_converter(self.controlState['steer'])
        pywinauto.mouse.release(button='left', coords=(t[0], t[1]))

    def brakeOn(self):
        self.controlState['brake'] = True
        t = self.steer_converter(self.controlState['steer'])
        pywinauto.mouse.press(button='right', coords=(t[0], t[1]))

    def brakeOff(self):
        self.controlState['brake'] = False
        t = self.steer_converter(self.controlState['steer'])
        pywinauto.mouse.release(button='right', coords=(t[0], t[1]))

    def run(self):
        while True:
            try:
                message = self.r.hget('pcars_action'+local_ip,self.local_ip)
                force_acc = self.r.hget('pcars_force_acc', self.local_ip)

                if force_acc:

                    if eval(force_acc) == True:
                        self.accOn()
                        
                        self.r.hdel('pcars_force_acc',self.local_ip)

                if message:
                    action = eval(message)
                    if action is False:
                        print("Control OFF")
                        self.move_steer(0)
                        self.brakeOff()
                        self.accOff()
                    else:
                        self.action_parser(action)

                    self.r.hdel('pcars_action'+self.local_ip,self.local_ip)
            except:
                pass

if __name__ == '__main__':
    ''' Getting Local IP of this Computer '''
    local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]

    ''' Init Redis '''
    r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
    
    pc = pCarsAutoController()
    while True:
        try:
            message = r.hget('pcars_action'+local_ip,local_ip)
            force_acc = r.hget('pcars_force_acc', local_ip)

            if force_acc:

                if eval(force_acc) == True:
                    pc.accOn()
                    
                    r.hdel('pcars_force_acc',local_ip)

            if message:
                action = eval(message)
                if action is False:
                    print("Control OFF")
                    pc.move_steer(0)
                    pc.brakeOff()
                    pc.accOff()
                else:
                    pc.action_parser(action)

                r.hdel('pcars_action'+local_ip,local_ip)
        except:
            pass








