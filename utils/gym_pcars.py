import numpy as np
import redis
import math

import numpy as np
import copy
import collections as col
import os
import subprocess
import time
import signal
from numpy import linalg as la
from datetime import datetime
from numpy import linalg as ln

class PcarsEnv:
    default_speed = 50
    speed_ok = False
    initial_reset = True
    time_step = 0

    def __init__(self, _map):
        self.torcs_proc = None
        self.initial_run = True
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

        # Variables
        self.position = []
        self.prevLapDistance = 0
        self.prevPosition = None
        self.ref_prevPosition = None
        self.distance = 0
        self.v_ref = 26

        self.brake_cnt = 0
        self.stop_cnt = 0
        self.backward_cnt = 0
        self.tyre_out_cnt = 0
        self.crash_cnt = 0
        self.stay_cnt = 0
        
        self.brake_time = None
        self.stop_time = None
        self.backward_time = None
        self.tyre_out_time = None
        self.crash_time = None
        self.stay_time = None

        # Grid Line
        self.grid_line = np.load('./utils/grid_line/'+_map+'.npz')['results'][:,1:4]
        self.distance_ref = np.load('./utils/grid_line/'+_map+'.npz')['results'][:,0]

        self.fp_x = self.grid_line[:,0].astype(float)
        self.fp_y = self.grid_line[:,1].astype(float)
        self.fp_z = self.grid_line[:,2].astype(float)

        self.reward = 0
        self.reset_amt = 0

    def one_hot(self, label, n_classes):
        a = np.zeros(n_classes)
        a[label] = 1
        return a

    def step_discrete(self, u, a_t, obs, target_ip, screen, worker_number):
        if 'raceState' in obs:

            j=0
            position=[]
            this_action = self.agent_to_torcs_discrete(u)
            terminate_status = False

            # Send Action Signal
            self.r.hset('pcars_action'+target_ip, target_ip, this_action)

            gameState = [int(s) for s in obs["gameState"].split('>')[0].split() if s.isdigit()][0]
            raceState = [int(s) for s in obs["raceState"].split('>')[0].split() if s.isdigit()][0]

            sp = obs["speed"]
            self.distance = obs["participants"][0]["currentLapDistance"]
            crashState = obs["crashState"]
            cur_position_x = obs["participants"][0]["worldPositionX"]
            cur_position_y = obs["participants"][0]["worldPositionY"]
            cur_position_z = obs["participants"][0]["worldPositionZ"]

            # print(cur_position_x, cur_position_y, cur_position_z)
            cur_position = np.array([cur_position_x,cur_position_y,cur_position_z])
            # ref_position_x = np.interp(cur_position_x, self.xp, self.fp_x)
            # ref_position_y = np.interp(cur_position_y, self.xp, self.fp_y)
            # ref_position_z = np.interp(cur_position_z, self.xp, self.fp_z)
            # ref_position = np.array([ref_position_x,ref_position_y,ref_position_z])
            if 0 < self.distance < 10000:
                # ref_position = self.grid_line[self.distance]
                ref_position_x = np.interp(self.distance, self.distance_ref, self.fp_x)
                ref_position_y = np.interp(self.distance, self.distance_ref, self.fp_y)
                ref_position_z = np.interp(self.distance, self.distance_ref, self.fp_z)

                ref_position = np.array([ref_position_x, ref_position_y, ref_position_z])
                # print("REF:",ref_position)
                # print("CUR:",cur_position)

                if self.ref_prevPosition is None and self.distance >= 1:
                    ref_position_x = np.interp(self.distance-1, self.distance_ref, self.fp_x)
                    ref_position_y = np.interp(self.distance-1, self.distance_ref, self.fp_y)
                    ref_position_z = np.interp(self.distance-1, self.distance_ref, self.fp_z)

                    self.ref_prevPosition = np.array([ref_position_x, ref_position_y, ref_position_z])

            else:
                ref_position = self.grid_line[1]

            def norm_np(n):
                n0 = n[0]
                n1 = n[1]
                n2 = n[2]

                ns = math.sqrt(n0*n0 + n1*n1 + n2*n2)
                # print(n0,n1,n2,ns)
                if ns == 0 or ns == 0.0:
                    return np.array([n0,n1,n2])
                else:
                    return np.array([n0/ns,n1/ns,n2/ns])

            def get_distance(p1,p2):
                r = p1-p2
                return math.sqrt(r[0]*r[0]+r[1]*r[1]+r[2]*r[2])

            # SP rectify
            # max_sp = 26
            # if sp > max_sp:
            #     sp = max_sp * 2 - sp

            # print("Distance",)
            screen.update("Distance : "+str(self.distance), worker_number, 'distance')
            # Reward 
            if self.distance != 0 and self.distance < 64000:
                # print(ref_position)
                # print(self.ref_prevPosition)
                # print(np.any(ref_position != self.ref_prevPosition))
                if self.prevPosition is not None and self.ref_prevPosition is not None and np.any(cur_position != self.prevPosition):
                    # d = abs(get_distance(ref_position,cur_position)) / 6
                    # v_e = cur_position - self.prevPosition
                    # v_r = ref_position - self.ref_prevPosition

                    # if d > 1:
                    #     d = 1 + (d-1) * 0.1

                    # cos_a = np.dot(norm_np(v_e),norm_np(v_r))

                    # screen.update("d : "+str(d), worker_number, 'd')
                    # screen.update("cos_a_1 : "+str(cos_a), worker_number, 'cos_a')

                    # progress = (sp * 10)*(cos_a - d)
                    # progress = (sp * 10)*(cos_a)
                    p_ref = np.append(ref_position, self.ref_prevPosition)
                    p = np.append(cur_position, self.prevPosition)
                    progress = -abs(self.v_ref - sp)-ln.norm(p_ref - p)
                    
                    # if progress < 0:
                    #     progress = 0

                    self.reward = progress
                
                elif self.ref_prevPosition is not None:
                    # d = abs(get_distance(ref_position,cur_position)) / 6
                    # v_e = cur_position - self.ref_prevPosition
                    # v_r = ref_position - self.ref_prevPosition

                    # if d > 1:
                    #     d = 1 + (d-1) * 0.1

                    # cos_a = np.dot(norm_np(v_e),norm_np(v_r))
                    # screen.update("d : "+str(d), worker_number, 'd')
                    # screen.update("cos_a_2 : "+str(cos_a), worker_number, 'cos_a')
                    # progress = (sp * 10)*(cos_a - d)
                    # progress = (sp * 10)*(cos_a)
                    p_ref = np.append(ref_position, self.ref_prevPosition)
                    p = np.append(cur_position, self.prevPosition)
                    progress = -abs(self.v_ref - sp)-ln.norm(p_ref - p)

                    # if progress < 0:
                    #     progress = 0
                        
                    self.reward = progress

                    if np.any(cur_position != self.prevPosition):
                        self.prevPosition = cur_position
                else:
                    progress = sp * 10

                    if progress < 0:
                        progress = 0
                        
                    self.reward = progress
            else:
                # print("prevPosition",self.prevPosition)
                if self.prevPosition is not None:
                    ref_position = self.grid_line[1]
                    
                    # d = abs(get_distance(ref_position,cur_position)) / 6
                    # v_e = cur_position - self.prevPosition
                    # v_r = ref_position - self.prevPosition

                    # if d > 1:
                    #     d = 1 + (d-1) * 0.1

                    # cos_a = np.dot(norm_np(v_e),norm_np(v_r))
                    # screen.update("d : "+str(d), worker_number, 'd')
                    # screen.update("cos_a_3 : "+str(cos_a), worker_number, 'cos_a')
                    # progress = (sp * 10)*(cos_a - d)
                    # progress = (sp * 10)*(cos_a)
                    p_ref = np.append(ref_position, self.ref_prevPosition)
                    p = np.append(cur_position, self.prevPosition)
                    progress = -abs(self.v_ref - sp)-ln.norm(p_ref - p)

                    self.reward = progress

                else : 
                    progress = sp * 10
                    self.reward = progress

            if self.prevPosition is None:
                self.prevPosition = cur_position

            if self.prevPosition is not None and np.all(cur_position != self.prevPosition):
                self.prevPosition = cur_position

                if np.any(ref_position != self.ref_prevPosition):
                    if self.distance > 1:
                        ref_position_x = np.interp(self.distance-1, self.distance_ref, self.fp_x)
                        ref_position_y = np.interp(self.distance-1, self.distance_ref, self.fp_y)
                        ref_position_z = np.interp(self.distance-1, self.distance_ref, self.fp_z)

                        self.ref_prevPosition = np.array([ref_position_x, ref_position_y, ref_position_z])

            self.prevLapDistance = self.distance
            self.time_step += 1

            if self.distance > 0:
                if len(self.position) == 20:
                    del self.position[0]
                    self.position.append(self.distance)
                    
                    if abs(self.position[19]-self.position[0]) < 10:
                        self.backward_cnt += 1
                        self.backward_time = datetime.now()
                        
                else:
                    self.position.append(self.distance)

            if self.distance == 0:
                if "gear" in obs:
                    if int(obs["gear"]) == 15:
                        self.brake_cnt += 1
                        self.brake_time = datetime.now()

            if sp < 0.0000001:
                self.stop_cnt += 1
                self.stop_time = datetime.now()
                        
            if "tyres" in obs:
                tireTerrains = obs["tyres"]
                
                _out_tyres = 0
                for i in range(4):
                    if tireTerrains[i]['terrain'] != 0 :  # Episode is terminated if the car is out of track
                        _out_tyres+=1

                if _out_tyres >= 2:
                    self.tyre_out_cnt += 1
                    self.tyre_out_time = datetime.now()

                if _out_tyres == 0:
                    self.tyre_out_cnt = 0
                    self.tyre_out_time = datetime.now()
                            
            if crashState >= 1:
                # print("Crash!", target_ip)
                if crashState == 1:
                    self.crash_cnt += 1
                elif crashState > 2:
                    self.crash_cnt += 3
                else : 
                    self.crash_cnt += 2

                self.crash_time = datetime.now()

            '''
            Reset Minus Flags based on current time.
            '''
            cur_time = datetime.now()
            reset_time = 5
            if self.backward_time is not None:
                delta = cur_time - self.backward_time
                if delta.seconds > reset_time:
                    self.backward_cnt = 0

            if self.brake_time is not None:
                delta = cur_time - self.brake_time
                if delta.seconds > reset_time:
                    self.brake_cnt = 0

            if self.stop_time is not None:
                delta = cur_time - self.stop_time
                if delta.seconds > reset_time:
                    self.stop_cnt = 0

            if self.tyre_out_time is not None:
                delta = cur_time - self.tyre_out_time
                if delta.seconds > reset_time and self.stop_cnt == 0:
                    self.tyre_out_cnt = 0

            if self.crash_time is not None:
                delta = cur_time - self.crash_time
                if delta.seconds > reset_time and self.tyre_out_cnt == 0:
                    self.crash_cnt = 0

            if self.time_step > 99:
                if self.distance == 0:
                    if self.stay_time is None:
                        self.stay_time = datetime.now()

                    if cur_time > self.stay_time:
                        self.stay_cnt += (cur_time - self.stay_time).seconds * 2
                    else:
                        self.stay_cnt += (self.stay_time - cur_time).seconds * 2

                else:
                    self.stay_cnt = 0
                    self.stay_time = None
                

            '''
            Minus Rewards
            '''
            self.reset_amt = 0
            d_factor = 10
            if self.stay_cnt > 0:
                self.reset_amt += -0.1 * self.stay_cnt / d_factor

            if self.backward_cnt > 0:
                self.reset_amt += -10 * self.backward_cnt / d_factor

            if self.brake_cnt > 0:
                self.reset_amt += -1 * self.brake_cnt / d_factor

            if self.stop_cnt > 0:
                self.reset_amt += -5 * self.stop_cnt / d_factor
                # pass

            if self.tyre_out_cnt > 0:
                self.reset_amt += -2 * self.tyre_out_cnt / d_factor
                # 타이어 나갈 시 리워드 감소.
                self.reward -= (sp * 10)(self.tyre_out_cnt * 0.01)

            if self.crash_cnt > 0:
                self.reset_amt += -1 * self.crash_cnt / d_factor

            # if self.distance == 65535:
            #     print("Bad Distance", target_ip)
            #     self.reset_amt = -200

            race_action = self.one_hot(a_t, 31)
            race_action = np.append(race_action, sp)
            # race_action = np.append(race_action, self.backward_cnt / 100)
            # race_action = np.append(race_action, self.tyre_out_cnt / 30)
            # race_action = np.append(race_action, self.crash_cnt / 10)
            race_action.astype(np.float32)
            race_action = race_action[np.newaxis,:]

            # print("###", self.backward_cnt / 100, self.tyre_out_cnt / 30, self.crash_cnt / 10)
            # print("Race Action 2:",race_action)
                
            # print("reward:", self.reward, target_ip)
            screen.update("reward : "+str(self.reward), worker_number, 'reward')
            screen.update("reset_ : "+str(self.reset_amt), worker_number, 'reset_amt')
            screen.update("B / T / C : "+str(self.backward_cnt / 100) + ', '+str(self.tyre_out_cnt / 100) + ', '+str(self.crash_cnt / 100), worker_number, 'reset_cnt')

            if self.reset_amt <= -100 and terminate_status is False:
                # print("Restarting by finish", gameState, raceState)
                self.brake_cnt = 0
                self.stop_cnt = 0
                self.backward_cnt = 0
                self.tyre_out_cnt = 0
                self.crash_cnt = 0
                self.stay_cnt = 0

                self.position = []
                self.distance = 0
                self.time_step = 0

                self.r.hset('pcars_action'+target_ip, target_ip, False)
                self.reset_pcars_4(target_ip)
                terminate_status = True

            return obs, self.reward, {}, terminate_status, race_action

   
    def reset_pcars(self,target_ip):
        # print("KILLER", target_ip)
        self.r.hset('pcars_killer'+target_ip,target_ip,"1")

    def reset_pcars_2(self,target_ip):
        self.r.hset('pcars_killer'+target_ip,target_ip,"2")

    def reset_pcars_3(self,target_ip):
        self.r.hset('pcars_killer'+target_ip,target_ip,"3")

    def reset_pcars_4(self,target_ip):
        self.r.hset('pcars_killer'+target_ip,target_ip,"4")

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
        torcs_action.update({'23': u[23]})
        torcs_action.update({'24': u[24]})
        torcs_action.update({'25': u[25]})
        torcs_action.update({'26': u[26]})
        torcs_action.update({'27': u[27]})
        torcs_action.update({'28': u[28]})
        torcs_action.update({'29': u[29]})
        torcs_action.update({'30': u[30]})

        # else:
        #     for i in range(23):
        #         torcs_action.update({str(i): u[8]})

        return torcs_action
