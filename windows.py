from utils.keys import Keys
from time import sleep
from datetime import datetime
keys = Keys()

reboot_time = 3600 # in seconds
print("Reboot in " + str(reboot_time) + "s.")
print("Project Cars will be launched in 10s.")
sleep(10)
# mouse movement
for i in range(100):
    keys.directMouse(-1*i, -1*i)
    # sleep(0.004)

keys.directMouse(buttons=keys.mouse_lb_press)
sleep(0.1)
keys.directMouse(buttons=keys.mouse_lb_release)

def key_input(key):
    keys.directKey(key)
    sleep(0.04)
    keys.directKey(key, keys.key_release)

for key in "project":
    key_input(key)

key_input("Return")
print("Waiting for Pcars to be launched for 30s.")
sleep(30)

from pywinauto.application import Application
import pywinauto

import win32ui
import win32gui
import win32com.client

def get_focus():
    # Make Pcars window focused
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys('%')
    
    PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
    PyCWnd1.SetForegroundWindow()
    PyCWnd1.SetFocus()

    return PyCWnd1

get_focus()
key_input("j")

for i in range(5):
    key_input("Left")
    key_input("Up")

key_input("Right")
key_input("Return")

sleep(1)
get_focus()
for i in range(5):
    key_input("Left")
    key_input("Up")

key_input("Return")

import os

stime = datetime.now()
while True:
    ctime = datetime.now()
    delta = ctime - stime
    
    if delta.seconds > reboot_time:
        print("Rebooting")
        os.system('shutdown /f /r /t 1')
        break
    else:
        sleep(1)