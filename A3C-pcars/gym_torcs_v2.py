# import gym
# from gym import spaces
import numpy as np
# from os import path
# import snakeoil3_gym as snakeoil3
import numpy as np
import copy
import collections as col
import os
import subprocess
import time
import signal
from DDPG import utils
from DDPG import autoController
import win32ui
import serial
import serial.tools.list_ports
from pywinauto.keyboard import SendKeys

class TorcsEnv:
    terminal_judge_start = 100  # Speed limit is applied after this step
    termination_limit_progress = 5  # [km/h], episode terminates if car is running slower than this limit
    default_speed = 50
    speed_ok = False
    initial_reset = True
    pc = autoController.pCarsAutoController()
    time_step = 0

    def __init__(self, port=3101):
        self.port = port
        self.torcs_proc = None
        self.initial_run = True
        self.prevLapDistance = 0
        self.target_ip = 'localhost:8080'
        self.get_focus()
        self.connect_arduino()


    def step_discrete(self, u):

        this_action = self.agent_to_torcs_discrete(u)

        # Steering
        if this_action['0'] == True:
            self.pc.move_steer(-1)
        elif this_action['1'] == True:
            self.pc.move_steer(-7.5)
        elif this_action['2'] == True:
            self.pc.move_steer(-5)
        elif this_action['3'] == True:
            self.pc.move_steer(-2.5)
        elif this_action['4'] == True:
            self.pc.move_steer(0)
        elif this_action['5'] == True:
            self.pc.move_steer(2.5)
        elif this_action['6'] == True:
            self.pc.move_steer(5)
        elif this_action['7'] == True:
            self.pc.move_steer(7.5)
        elif this_action['8'] == True:
            self.pc.move_steer(1)
        elif this_action['9'] == True:
            self.pc.move_steer(-1)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['10'] == True:
            self.pc.move_steer(-7.5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['11'] == True:
            self.pc.move_steer(-5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['12'] == True:
            self.pc.move_steer(-2.5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['13'] == True:
            self.pc.move_steer(0)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['14'] == True:
            self.pc.move_steer(2.5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['15'] == True:
            self.pc.move_steer(5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['16'] == True:
            self.pc.move_steer(7.5)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['17'] == True:
            self.pc.move_steer(1)
            self.pc.accOn()
            time.sleep(0.6)
            self.pc.accOff()
        elif this_action['18'] == True:
            self.pc.brakeOn()
            time.sleep(0.5)
            self.pc.brakeOff()

        obs = utils.send_crest_requset(self.target_ip, "crest-monitor", {})

        # angle = obs["motionAndDeviceRelated"]["mOrientation"][1]
        raceState = obs["gameStates"]["mRaceState"]
        sp = obs["carState"]["mSpeed"]
        distance = obs["participants"]["mParticipantInfo"][0]["mCurrentLapDistance"]
        crashState = obs["carDamage"]["mCrashState"]
        tireTerrain = obs["wheelsAndTyres"]["mTerrain"]

        progress = sp * distance + sp * sp
        reward = progress / 1000

        if raceState == 3:
            reward = -200
            self.reset_pcars_2()

        if distance == 0 and obs["carState"]["mBrake"] ==1:
            reward = -200
            self.reset_pcars()

        if tireTerrain.count(0) == 0 :  # Episode is terminated if the car is out of track
            reward = -200
            self.reset_pcars()
       
        if crashState > 1:
            reward = -200
            self.reset_pcars()

        elif sp < 0.05:
            reward = -200
            self.reset_pcars()

        if self.prevLapDistance != 0 and distance != 0 and distance <= self.prevLapDistance:  # Episode is terminated if the agent runs backward
            reward = -200
            self.reset_pcars()
        
        self.prevLapDistance = distance
        self.time_step += 1

        print(reward)
        return obs, reward, {}
   
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
        return True

    def end(self):
        os.killpg(os.getpgid(self.torcs_proc.pid), signal.SIGKILL)

    def reset_pcars(self):
        self.time_step = 0
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
        while True:
            gameData = utils.send_crest_requset(self.target_ip, "crest-monitor", {})
            gameState = gameData["gameStates"]["mRaceState"]

            if gameState == 2:
                break

        self.ard.close()
        self.connect_arduino()
        return True
   
    def reset_pcars_2(self):
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
        while True:
            gameData = utils.send_crest_requset(self.target_ip, "crest-monitor", {})
            raceState = gameData["gameStates"]["mRaceState"]

            if raceState < 3:
                break
        
        return True

    def agent_to_torcs_discrete(self, u):
        torcs_action = {'0': u[0]}
        torcs_action.update({'1': u[1]})
        torcs_action.update({'2': u[2]})
        torcs_action.update({'3': u[3]})
        torcs_action.update({'4': u[4]})
        torcs_action.update({'5': u[5]})
        torcs_action.update({'6': u[6]})
        torcs_action.update({'7': u[7]})
        torcs_action.update({'8': u[8]})
        torcs_action.update({'9': u[9]})
        torcs_action.update({'10': u[10]})
        torcs_action.update({'11': u[11]})
        torcs_action.update({'12': u[12]})
        torcs_action.update({'13': u[13]})
        torcs_action.update({'14': u[14]})
        torcs_action.update({'15': u[15]})
        torcs_action.update({'16': u[16]})
        torcs_action.update({'17': u[17]})
        torcs_action.update({'18': u[18]})

        return torcs_action
