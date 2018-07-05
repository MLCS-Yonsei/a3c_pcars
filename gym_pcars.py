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
        self.distance = 0
        self.brake_cnt = 0
        self.prevPosition = None
        self.ref_prevPosition = None
        self.grid_line = np.load('grid_line.npz')['results']
        self.xp = self.grid_line[:,0]
        self.fp_x = self.grid_line[:,1]
        self.fp_y = self.grid_line[:,2]
        self.fp_z = self.grid_line[:,3]
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
        self.reward = 0
        self.position = []

   
    def step_discrete(self, u, obs, target_ip):
        if 'raceState' in obs:

            j=0; position=[]
            this_action = self.agent_to_torcs_discrete(u)
            terminate_status = False
            # print(u, this_action)
            # Steering
            self.r.hset('pcars_action'+target_ip, target_ip, this_action)

            # angle = obs["motionAndDeviceRelated"]["mOrientation"][1]
            
            raceState = [int(s) for s in obs["raceState"].split('>')[0].split() if s.isdigit()][0]
            #raceState = int(raceState)
            if raceState == 3:
                self.reward = -300
                self.reset_pcars_2(target_ip)
                terminate_status = True

            sp = obs["speed"]
            self.distance = obs["participants"][0]["currentLapDistance"]
            crashState = obs["crashState"]
            cur_position_x = obs["participants"][0]["worldPositionX"]
            cur_position_y = obs["participants"][0]["worldPositionY"]
            cur_position_z = obs["participants"][0]["worldPositionZ"]
            cur_position = np.array([cur_position_x,cur_position_y,cur_position_z])
            ref_position_x = np.interp(cur_position_x, self.xp, self.fp_x)
            ref_position_y = np.interp(cur_position_y, self.xp, self.fp_y)
            ref_position_z = np.interp(cur_position_z, self.xp, self.fp_z)
            ref_position = np.array([ref_position_x,ref_position_y,ref_position_z])

            print("Distance",self.distance)
            # Reward 
            if self.distance != 0 and self.distance != 65535:
                if self.prevPosition is not None:
                    d = la.norm(ref_position-cur_position) / 5
                    v_e = cur_position - self.prevPosition
                    v_r = ref_position - self.ref_prevPosition

                    cos_a = np.dot(v_e,v_r) / 20

                    progress = (sp/200)*(cos_a - d)
                    self.reward = progress / 10
                
                    #if sp < 0.01:
                    #    reward = -200
                    #    self.reset_pcars(target_ip)

                    # if self.prevLapDistance != 0 and self.prevLapDistance != 78 and (self.distance - self.prevLapDistance) < 0:
                    #     self.prevLapDistance = 0
                    #     self.reward = -200
                    #     print("backward:",self.prevLapDistance, self.distance)

                    #if self.prevLapDistance != 0 and distance != 0 and distance <= self.prevLapDistance:  # Episode is terminated if the agent runs backward
                    #    reward = -200
                    #    self.reset_pcars(target_ip)
                    
            
            else:
                if self.prevPosition is not None:
                    v_e = cur_position - self.prevPosition
                    v_r = ref_position - self.ref_prevPosition
                    cos_a = np.dot(v_e,v_r) / 20

                    self.reward = sp*cos_a
                else : 
                    self.reward = sp*sp

            self.prevPosition = cur_position
            self.prevLapDistance = self.distance
            self.time_step += 1
            self.ref_prevPosition = ref_position

            if self.distance > 0:
                if len(self.position) == 20:
                    del self.position[0]
                    self.position.append(self.distance)
                    
                    if abs(self.position[19]-self.position[0]) < 10:
                        print(self.position)
                        
                        self.reward = -200
                else:
                    self.position.append(self.distance)

            if self.distance == 0:
                if "gear" in obs:
                    if int(obs["gear"]) == 15:
                        self.brake_cnt = self.brake_cnt + 1

                        if self.brake_cnt > 30:
                            print("too much brakes")
                            self.reward = -200

            if self.distance == 0 and obs['brake'] == 1:
                self.brake_cnt = self.brake_cnt + 1
                if self.brake_cnt > 30:
                    print("too much brakes")
                    self.reward = -200

            if "tyres" in obs:
                tireTerrain = obs["tyres"]
                for i in range(4):
                    if tireTerrain[i]['terrain'] != 0 :  # Episode is terminated if the car is out of track
                        j+=1
                if j >= 2:
                    self.reward = -200; j = 0

            if crashState > 1:
                self.reward = -200

            if self.distance == 65535:
                self.reward = -200

            print("reward:86:",self.reward,target_ip)
            if self.reward == -200:
                print("Restarting")
                self.brake_cnt = 0
                self.position = []
                self.distance = 0
                self.time_step = 0

                self.reset_pcars(target_ip)
                terminate_status = True

            return obs, self.reward, {}, terminate_status

   
    def reset_pcars(self,target_ip):
        print("KILLER", target_ip)
        self.r.hset('pcars_killer'+target_ip,target_ip,"1")

    def reset_pcars_2(self,target_ip):
        self.r.hset('pcars_killer'+target_ip,target_ip,"2")

    def reset_pcars_3(self,target_ip):
        self.r.hset('pcars_killer'+target_ip,target_ip,"3")

    def agent_to_torcs_discrete(self, u):
        # if self.distance != 0:
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
        # else:
        #     for i in range(23):
        #         torcs_action.update({str(i): u[8]})


        return torcs_action
