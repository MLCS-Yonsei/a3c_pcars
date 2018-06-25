# import gym
# from gym import spaces
import numpy as np
import redis
# from os import path
# import snakeoil3_gym as snakeoil3
import numpy as np
import copy
import collections as col
import os
import subprocess
import time
import signal
#from DDPG import utils
#from DDPG import autoController
#import win32ui
#import serial
#import serial.tools.list_ports
#from pywinauto.keyboard import SendKeys


class PcarsEnv:
    default_speed = 50
    speed_ok = False
    initial_reset = True
    time_step = 0

    def __init__(self, port=3101):
        self.torcs_proc = None
        self.initial_run = True
        self.prevLapDistance = 0

        self.r = redis.StrictRedis(host='lab.hwanmoo.kr', port=6379, db=1)

   
    def step_discrete(self, u, obs, target_ip):
        j=0 
        this_action = self.agent_to_torcs_discrete(u)

        # Steering
        self.r.hset('pcars_action', target_ip, this_action)

        # angle = obs["motionAndDeviceRelated"]["mOrientation"][1]
        
        if "raceState" in obs and obs["raceState"] =='<RaceState.RACING: 2>' and obs["raceState"] != '<RaceState.INVALID: 0>':
            raceState = obs["raceState"].replace('<RaceState.RACING: ','')
            raceState = raceState.replace('>','')#;print(type(raceState))
            #raceState = int(raceState)
            if raceState == '3':
                reward = -200
                self.reset_pcars_2(target_ip)

            sp = obs["speed"]
            distance = obs["participants"][0]["currentLapDistance"]
            crashState = obs["crashState"]
            tireTerrain = obs["tyres"]

            progress = sp * distance + sp * sp
            reward = progress / 10
         
            if distance == 0 and obs['brake'] == 1:
                reward = -200
                self.reset_pcars(target_ip)

            for i in range(4):
                if tireTerrain[i]['terrain'] == 7 :  # Episode is terminated if the car is out of track
                    j+=1;print(tireTerrain[i]['terrain'])
            if j >= 3:
                reward = -200; j = 0
                self.reset_pcars(target_ip)
       
            if crashState > 1:
                reward = -200
                self.reset_pcars(target_ip)

            #if sp < 0.01:
            #    reward = -200
            #    self.reset_pcars(target_ip)
            if self.prevLapDistance != 0 and self.prevLapDistance != 78 and abs(self.prevLapDistance - distance) < 1:
                reward = -200;print(self.prevLapDistance, distance)
                self.reset_pcars(target_ip)

            #if self.prevLapDistance != 0 and distance != 0 and distance <= self.prevLapDistance:  # Episode is terminated if the agent runs backward
            #    reward = -200
            #    self.reset_pcars(target_ip)
        
            self.prevLapDistance = distance
            self.time_step += 1

            print(reward)
            return obs, reward, {}
        else:
            pass
   
    def reset_pcars(self,target_ip):
        self.r.hset('pcars_killer',target_ip,"1")

    def reset_pcars_2(self,target_ip):
        self.r.hset('pcars_killer',target_ip,"2")

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
