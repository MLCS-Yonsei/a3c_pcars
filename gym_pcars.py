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
from numpy import linalg as la
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

        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

   
    def step_discrete(self, u, obs, target_ip):
        if 'raceState' in obs:
            try:
                j=0; position=[]
                this_action = self.agent_to_torcs_discrete(u)
                terminate_status = False

                # Steering
                self.r.hset('pcars_action', target_ip, this_action)

                # angle = obs["motionAndDeviceRelated"]["mOrientation"][1]
                
                raceState = [int(s) for s in obs["raceState"].split('>')[0].split() if s.isdigit()][0]
                #raceState = int(raceState)
                if raceState == 3:
                    reward = -300
                    self.reset_pcars_2(target_ip)
                    terminate_status = True

                sp = obs["speed"]
                distance = obs["participants"][0]["currentLapDistance"]
                crashState = obs["crashState"]

                
                # Reward 
                if distance != 0:
                    d = la.norm(ref[int(distance)]-distance)
                    v_e = distance - self.prevLapDistance
                    v_r = ref[int(distance)] - ref[int(distance)-1]
                    cos_a = np.dot(v_e/la.norm(v_e),v_r/la.norm(v_r))

                    progress = sp*(cos_a - d)
                    reward = progress / 10
                
                    if distance == 0 and obs['brake'] == 1:
                        reward = -200

                    if "tyres" in obs:
                        tireTerrain = obs["tyres"]
                        for i in range(4):
                            if tireTerrain[i]['terrain'] != 0 :  # Episode is terminated if the car is out of track
                                j+=1
                        if j >= 3:
                            reward = -200; j = 0

                    if crashState > 1:
                        reward = -200

                    #if sp < 0.01:
                    #    reward = -200
                    #    self.reset_pcars(target_ip)
                    if self.prevLapDistance != 0 and self.prevLapDistance != 78 and (distance - self.prevLapDistance) < 1:
                        reward = -200;print("backward:",self.prevLapDistance, distance)

                    #if self.prevLapDistance != 0 and distance != 0 and distance <= self.prevLapDistance:  # Episode is terminated if the agent runs backward
                    #    reward = -200
                    #    self.reset_pcars(target_ip)
                    if len(position) == 50:
                        position = position[1:].append(distance)
                        if abs(position[0]-position[50]) < 50:
                            reward = -200
                    else:
                        position.append(distance)

                    self.prevLapDistance = distance
                    self.time_step += 1
                
                else:
                    reward = sp*sp

                    self.prevLapDistance = distance
                    self.time_step += 1

                print("reward:86:",reward)
                if reward == -200:
                    print("Restarting")
                    self.reset_pcars(target_ip)
                    terminate_status = True

                return obs, reward, {}, terminate_status
            except Exception as ex:
                print("Error on step_discrete:",ex)
   
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
        torcs_action.update({'19': u[19]})
        torcs_action.update({'20': u[20]})
        torcs_action.update({'21': u[21]})
        torcs_action.update({'22': u[22]})

        return torcs_action
