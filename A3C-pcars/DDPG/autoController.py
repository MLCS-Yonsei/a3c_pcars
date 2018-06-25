from pywinauto.application import Application
import pywinauto

import win32ui
import win32gui

import serial
import serial.tools.list_ports

# from utils import send_crest_requset
import multiprocessing as mp
import time
import json

class pCarsAutoController(mp.Process):
    def __init__(self):
        super(pCarsAutoController,self).__init__()

        self.get_focus()
        self.status = 'active'

        self.target_ip = 'localhost:8080'

        self.controlState = {
            'acc': False,
            'brake': False,
            'steer': 0
        }

        # self.svrsock = socket(AF_INET, SOCK_DGRAM)
        # self.svrsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # self.svrsock.bind(('192.168.0.49', 54545))               #로컬호스트에 5001포트로 바인딩

    def get_focus(self):
        # Make Pcars window focused
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

        return PyCWnd1

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
        zero = [x + int(w/2), y + int(h/2)]
        d = int(w/2 * n)

        t = [zero[0] + d, zero[1]]

        return t

    def move_steer(self, n):
        # self.controlState['steer'] = n
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
            if self.status == 'active':
                gameData = send_crest_requset(self.target_ip, "crest-monitor", {})

                # parse Game Data
                gameState = gameData["gameStates"]["mGameState"]
                if gameState > 1:
                    s, addr = self.svrsock.recvfrom(4096)

                    if s == b'Connect':
                        print('Connected')
                        self.svrsock.sendto('OK'.encode(),addr)
                    else:
                        print(s.decode())
                        self.controlState = json.loads(s.decode())
                        n = self.controlState['steer']

                        self.move_steer(n)
                        
                        if self.controlState['acc'] == True:
                            self.accOn()
                        
                        if self.controlState['acc'] == False:
                            self.accOff()

                        if self.controlState['brake'] == True:
                            self.brakeOn()
                        
                        if self.controlState['brake'] == False:
                            self.brakeOff()

if __name__ == '__main__':
    print(123)
    pc = pCarsAutoController()
    pc.move_steer(0.5)
    pc.accOn()
    time.sleep(5)
    exit(0)









