

import os
import argparse
import sys

from time import sleep
from datetime import datetime

import numpy as np
np.set_printoptions(threshold=np.inf)

import tensorflow as tf
import tensorflow.contrib.slim as slim
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import scipy.signal
import scipy.misc

import threading

import redis

import base64
from io import BytesIO
from PIL import Image
from skimage.transform import resize

from utils.helper import *
from utils.gym_pcars import PcarsEnv
from utils.seg.pred_road import *
from utils.pycurses import Screen

import curses

# Copies one set of variables to another.
# Used to set worker network parameters to those of global network.
def update_target_graph(from_scope, to_scope):
    from_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, from_scope)
    to_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, to_scope)

    op_holder = []
    for from_var, to_var in zip(from_vars, to_vars):
        op_holder.append(to_var.assign(from_var))
    return op_holder
   
# Processes Doom screen image to produce cropped and resized image.
def process_frame(frame):
    img = Image.fromarray(frame, 'RGB')
    
    s = np.asarray(img, dtype="uint8")
    s = np.reshape(s, [np.prod(s.shape)]) / 255.0

    return s


# Discounting function used to calculate discounted returns.
def discount(x, gamma):
    return scipy.signal.lfilter([1], [1, -gamma], x[::-1], axis=0)[::-1]


# Used to initialize weights for policy and value output layers
def normalized_columns_initializer(std=1.0):
    def _initializer(shape, dtype=None, partition_info=None):
        out = np.random.randn(*shape).astype(np.float32)
        out *= std / np.sqrt(np.square(out).sum(axis=0, keepdims=True))
        return tf.constant(out)

    return _initializer


class AC_Network:
    def __init__(self, s_size, a_size, scope, trainer, continuous=False):
        with tf.variable_scope(scope):
            # Input and visual encoding layers
            self.inputs = tf.placeholder(shape=[None, s_size], dtype=tf.float32)
            self.imageIn = tf.reshape(self.inputs, shape=[-1, 150, 200, 3])
            self.conv1 = slim.conv2d(activation_fn=tf.nn.elu,
                                     inputs=self.imageIn, num_outputs=16,
                                     kernel_size=[4, 8], stride=[1, 4], padding='VALID')
            self.conv2 = slim.conv2d(activation_fn=tf.nn.elu,
                                     inputs=self.conv1, num_outputs=32,
                                     kernel_size=[4, 8], stride=[1, 6], padding='VALID')
            self.conv3 = slim.conv2d(activation_fn=tf.nn.elu,
                                     inputs=self.conv1, num_outputs=32,
                                     kernel_size=[2, 4], stride=[1, 6], padding='VALID')
            hidden = slim.fully_connected(slim.flatten(self.conv3), 256, activation_fn=tf.nn.elu)
            self.racing_action = tf.placeholder(shape=[None, a_size+1], dtype=tf.float32, name="Racing_action")
            hidden = tf.concat([hidden, self.racing_action], 1)

            # Recurrent network for temporal dependencies
            lstm_cell = tf.contrib.rnn.BasicLSTMCell(256, state_is_tuple=True)
            c_init = np.zeros((1, lstm_cell.state_size.c), np.float32)
            h_init = np.zeros((1, lstm_cell.state_size.h), np.float32)
            self.state_init = [c_init, h_init]  # initial state of the rnn
            c_in = tf.placeholder(tf.float32, [1, lstm_cell.state_size.c])
            h_in = tf.placeholder(tf.float32, [1, lstm_cell.state_size.h])
            self.state_in = (c_in, h_in)
            rnn_in = tf.expand_dims(hidden, [0])
            step_size = tf.shape(self.imageIn)[:1]
            state_in = tf.contrib.rnn.LSTMStateTuple(c_in, h_in)
            lstm_outputs, lstm_state = tf.nn.dynamic_rnn(
                lstm_cell, rnn_in, initial_state=state_in, sequence_length=step_size,
                time_major=False)
            lstm_c, lstm_h = lstm_state
            self.state_out = (lstm_c[:1, :], lstm_h[:1, :])
            rnn_out = tf.reshape(lstm_outputs, [-1, 256])

            # Output layers for policy and value estimations
            self.discrete_policy = slim.fully_connected(rnn_out, a_size,
                                                        activation_fn=tf.nn.softmax,
                                                        weights_initializer=normalized_columns_initializer(0.01),
                                                        biases_initializer=None)
        

            self.value = slim.fully_connected(rnn_out, 1,
                                              activation_fn=None,
                                              weights_initializer=normalized_columns_initializer(1.0),
                                              biases_initializer=None)

            # Only the worker network need ops for loss functions and gradient updating.
            if scope != 'global':
                self.target_v = tf.placeholder(shape=[None], dtype=tf.float32)
                self.advantages = tf.placeholder(shape=[None], dtype=tf.float32)

                self.actions = tf.placeholder(shape=[None], dtype=tf.int32)
                self.actions_onehot = tf.one_hot(self.actions, a_size, dtype=tf.float32)

                self.responsible_outputs = tf.reduce_sum(self.discrete_policy * self.actions_onehot, [1])

                self.entropy_loss = - tf.reduce_sum(self.discrete_policy * tf.log(self.discrete_policy))
                self.policy_loss = -tf.reduce_sum(tf.log(self.responsible_outputs) * self.advantages)
                self.value_loss = 0.5 * tf.reduce_sum(tf.square(self.target_v - tf.reshape(self.value, [-1])))

                self.loss = 0.5 * self.value_loss + self.policy_loss - self.entropy_loss * 0.01

                # Get gradients from local network using local losses
                local_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope)
                self.gradients = tf.gradients(self.loss, local_vars)
                self.var_norms = tf.global_norm(local_vars)
                grads, self.grad_norms = tf.clip_by_global_norm(self.gradients, 40.0)

                # Apply local gradients to global network
                global_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, 'global')
                self.apply_grads = trainer.apply_gradients(zip(grads, global_vars))


class Worker:
    def __init__(self, env, name, s_size, a_size, trainer, model_path, global_episodes, continuous=False):
        self.continuous = continuous
        self.name = "worker_" + str(name)
        self.number = name
        self.model_path = model_path
        self.trainer = trainer
        self.global_episodes = global_episodes
        self.increment = self.global_episodes.assign_add(1)
        self.episode_rewards = []
        self.episode_lengths = []
        self.episode_mean_values = []
        self.summary_writer_train = tf.summary.FileWriter("./train/train_" + str(self.number))
        self.summary_writer_play = tf.summary.FileWriter("./play/play_" + str(self.number))

        ''' Init Redis '''
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

        # Create the local copy of the network and the tensorflow op to copy global params to local network
        self.local_AC = AC_Network(s_size, a_size, self.name, trainer, continuous)
        self.update_local_ops = update_target_graph('global', self.name)
        self.env = env
        if not continuous:
            self.actions = np.identity(a_size, dtype=bool).tolist()    #To have same format as doom

        self.restarting = False      

    def train(self, rollout, sess, gamma, bootstrap_value):
        rollout = np.array(rollout)
        observations = rollout[:, 0]
        actions = np.asarray(rollout[:, 1].tolist())
        rewards = rollout[:, 2]
        next_observations = rollout[:, 3]
        values = rollout[:, 5]
        race_action = np.vstack(rollout[:,6])

        # We take the rewards and values from rollout, and use them to generate the advantage and discounted returns.
        # The advantage function uses "Generalized Advantage Estimation"
        self.rewards_plus = np.asarray(rewards.tolist() + [bootstrap_value])
        discounted_rewards = discount(self.rewards_plus, gamma)[:-1]
        self.value_plus = np.asarray(values.tolist() + [bootstrap_value])
        advantages = rewards + gamma * self.value_plus[1:] - self.value_plus[:-1]
        advantages = discount(advantages, gamma)
        # print(advantages)
        # Update the global network using gradients from loss
        # Generate network statistics to periodically save
        rnn_state = self.local_AC.state_init
        if not self.continuous:
            feed_dict = {self.local_AC.target_v: discounted_rewards,
                         self.local_AC.inputs: np.vstack(observations),
                         self.local_AC.actions: actions,
                         self.local_AC.advantages: advantages,
                         self.local_AC.state_in[0]: rnn_state[0],
                         self.local_AC.state_in[1]: rnn_state[1],
                         self.local_AC.racing_action: race_action}
        else:
            feed_dict = {self.local_AC.target_v: discounted_rewards,
                         self.local_AC.inputs: np.vstack(observations),
                         self.local_AC.steer: actions[:, 0],
                         # self.local_AC.accelerate: actions[:, 1],
                         # self.local_AC.brake: actions[:, 2],
                         self.local_AC.advantages: advantages,
                         self.local_AC.state_in[0]: rnn_state[0],
                         self.local_AC.state_in[1]: rnn_state[1],
                         self.local_AC.racing_action: race_action}
        v_l, p_l, e_l, loss_f, g_n, v_n, _ = sess.run([self.local_AC.value_loss,
                                                       self.local_AC.policy_loss,
                                                       self.local_AC.entropy_loss,
                                                       self.local_AC.loss,
                                                       self.local_AC.grad_norms,
                                                       self.local_AC.var_norms,
                                                       self.local_AC.apply_grads],
                                                      feed_dict=feed_dict)
        return v_l / len(rollout), p_l / len(rollout), e_l / len(rollout), loss_f / len(rollout), g_n, v_n

    def parse_message(self,message):
        # Parse message from data_sender.py via redis
        message = message.decode("utf-8")
        message = message.replace('<','\'<')
        message = message.replace('>','>\'')

        msg = eval(message)
        ob = msg['game_data']
        s = msg['image_data']

        # Decode image within base64 
        s = base64.b64decode(s)
        s = Image.open(BytesIO(s))

        # s = s.resize((576,160), Image.ANTIALIAS)
        s = np.array(s)
        # print("#2", s.shape)
        # pimg = np.expand_dims(s, axis=0)
        # # print("Img shape", s.shape)
        # pred = pred_img(self.rs_sess, self.rs_input_tensor, self.rs_output_tensor, pimg)
        # pred = np.expand_dims(pred, axis=2)
        # print("#3", pred.shape)
        # s = np.concatenate((s, pred), axis=2)
        # s = resize(s, (150, 200), anti_aliasing=True)
        # print("#4", s.shape)
        
        return ob, s

    def work(self, max_episode_length, gamma, sess, coord, saver, training, target_ip, screen):
        # self.rs_sess = rs_sess
        # self.rs_input_tensor = rs_input_tensor
        # self.rs_output_tensor = rs_output_tensor

        episode_count = sess.run(self.global_episodes)
        total_steps = 0

        msg = "Worker " + str(self.number)
        screen.update(msg, self.number, 'worker_header')
        # self.r.hset('pcars_killer'+target_ip,target_ip,"3")
        with sess.as_default(), sess.graph.as_default():
            
            while not coord.should_stop():
                message = self.r.hget('pcars_data'+target_ip,target_ip)

                if message:
                    self.r.hdel('pcars_data'+target_ip,target_ip)
                    try:
                        ob, s = self.parse_message(message)

                        if 'raceState' in ob and 'gameState' in ob:

                            gameState = [int(s) for s in ob["gameState"].split('>')[0].split() if s.isdigit()][0]
                            raceState = [int(s) for s in ob["raceState"].split('>')[0].split() if s.isdigit()][0]

                            if raceState == 2 and gameState == 2:
                                msg = "Starting Episode" + str(episode_count) + target_ip
                                # screen.update(msg, self.number, "print")

                                # Set control OFF
                                self.r.hset('pcars_action'+target_ip, target_ip, False)
                                sess.run(self.update_local_ops)

                                episode_buffer = []
                                episode_values = []
                                episode_frames = []
                                episode_reward = 0
                                episode_step_count = 0

                                # terminate status
                                d = False

                                s = process_frame(s)
                                
                                # For creating gifs
                                to_gif = np.reshape(s, (150, 200, 3)) * 255
                                episode_frames.append(to_gif)
                                
                                rnn_state = self.local_AC.state_init
                                race_action = np.zeros((1, 32), np.float32)

                                while not d:
                                    t1 = datetime.now()
                                    while self.restarting:
                                        message = self.r.hget('pcars_killer'+target_ip,target_ip)

                                        if message:
                                            t0 = datetime.now()
                                            
                                            reset_status = eval(message)
                                            # print(t0, reset_status)
                                            # autoKiller에서 처리중
                                            if reset_status == 1:
                                                pass
                                            elif reset_status == 2:
                                                pass
                                            elif reset_status == 3:
                                                pass
                                            elif reset_status == 4:
                                                pass
                                            elif reset_status == 0:
                                                # print("out of First loop")
                                                self.restarting = False
                                                self.r.hdel('pcars_killer'+target_ip,target_ip)
                                                break
                                            else:
                                                # print("out of First loop")
                                                break
                                        else: 
                                            break

                                        t2 = datetime.now()
                                        delta = t2 - t1
                                        if delta.seconds > 20:
                                            t1 = datetime.now()
                                            # print("Force reset 1, type", 2)
                                            self.r.hset('pcars_killer'+target_ip,target_ip,"2")
                                    t1 = datetime.now()
                                    while self.restarting:
                                        message = self.r.hget('pcars_data'+target_ip,target_ip)

                                        if message:
                                            
                                            self.r.hdel('pcars_data'+target_ip,target_ip)
                                            ob, s = self.parse_message(message)

                                            if 'raceState' in ob and 'gameState' in ob and 'participants' in ob:

                                                gameState = [int(s) for s in ob["gameState"].split('>')[0].split() if s.isdigit()][0]
                                                raceState = [int(s) for s in ob["raceState"].split('>')[0].split() if s.isdigit()][0]
                                                sessionState = [int(s) for s in ob["sessionState"].split('>')[0].split() if s.isdigit()][0]
                                                lap_distance = ob["participants"][0]["currentLapDistance"]
                                                raceStateFlags = ob['raceStateFlags']
                                                # print("Restarting")
                                                # print(gameState, raceState, raceStateFlags)
                                                # print("R",gameState, raceState, sessionState, raceStateFlags)
                                                if gameState != 2 or (gameState == 2 and raceState == 2):
                                                    self.r.hdel('pcars_force_acc', target_ip)
                                                    self.restarting = False
                                                    self.r.hset('pcars_action'+target_ip, target_ip, False)
                                                    break
                                        
                                        t2 = datetime.now()
                                        delta = t2 - t1
                                        if delta.seconds > 20:
                                            t1 = datetime.now()
                                            # print("Force reset 2")
                                            self.r.hset('pcars_killer'+target_ip,target_ip,"1")

                                    # Get recent data
                                    message = self.r.hget('pcars_data'+target_ip,target_ip)

                                    if message:
                                        self.r.hdel('pcars_data'+target_ip,target_ip)
                                        ob, s = self.parse_message(message)

                                        if 'raceState' in ob and 'gameState' in ob and 'participants' in ob:

                                            gameState = [int(st) for st in ob["gameState"].split('>')[0].split() if st.isdigit()][0]
                                            raceState = [int(st) for st in ob["raceState"].split('>')[0].split() if st.isdigit()][0]
                                            sessionState = [int(s) for s in ob["sessionState"].split('>')[0].split() if s.isdigit()][0]
                                            lap_distance = ob["participants"][0]["currentLapDistance"]
                                            raceStateFlags = ob['raceStateFlags']
                                            # print("123",gameState, raceState, sessionState, raceStateFlags)

                                            if raceState == 2 and gameState == 2:
                                                s = process_frame(s)
                                                # Take an action using probabilities from policy network output.

                                                a_dist, v, rnn_state = sess.run(
                                                    [self.local_AC.discrete_policy, self.local_AC.value, self.local_AC.state_out],
                                                    feed_dict={self.local_AC.inputs: [s],
                                                            self.local_AC.state_in[0]: rnn_state[0],
                                                            self.local_AC.state_in[1]: rnn_state[1],
                                                            self.local_AC.racing_action: race_action})
                                                a_t = np.random.choice(a_dist[0], p=a_dist[0])  # a random sample is generated given probabs
                                                a_t = np.argmax(a_dist == a_t)
                                                
                                                _, reward, info, d, race_action = self.env.step_discrete(self.actions[a_t], a_t, ob, target_ip, screen, self.number)

                                                # r = reward/1000
                                                r = reward
                                                
                                                if not d:
                                                    message = self.r.hget('pcars_data'+target_ip,target_ip)
                                                    if message:
                                                        self.r.hdel('pcars_data'+target_ip,target_ip)
                                                        ob, s1 = self.parse_message(message)
                                                        s1 = process_frame(s1)
                                                    else:
                                                        s1 = s

                                                    # to_gif1 = np.reshape(s1, (150, 200, 4)) * 255
                                                    to_gif1 = np.reshape(s1, (150, 200, 3)) * 255

                                                    episode_frames.append(to_gif1)

                                                else:
                                                    s1 = s

                                                episode_buffer.append([s, a_t, r, s1, d, v[0, 0], race_action])
                                                episode_values.append(v[0, 0])

                                                episode_reward += r
                                                s = s1
                                                total_steps += 1
                                                episode_step_count += 1
                                                # print("episode ", episode_count, " step count :",episode_step_count, " Total Step :", total_steps)
                                                screen.update("Episode : " + str(episode_count), self.number, "episode")
                                                screen.update("Step : " + str(episode_step_count) + " (" + str(total_steps) + ")", self.number, "step")

                                                # If the episode hasn't ended, but the experience buffer is full, then we
                                                # make an update step using that experience rollout.
                                                if training and len(episode_buffer) == 100 and d is not True:  #batch to 100 30 before 
                                                    # Since we don't know what the true final return is, we "bootstrap" from our current
                                                    # value estimation
                                                    v1 = sess.run(self.local_AC.value,
                                                                feed_dict={self.local_AC.inputs: [s],
                                                                            self.local_AC.state_in[0]: rnn_state[0],
                                                                            self.local_AC.state_in[1]: rnn_state[1],
                                                                            self.local_AC.racing_action: race_action})[0, 0]
                                                    v_l, p_l, e_l, loss_f, g_n, v_n = self.train(episode_buffer, sess, gamma, v1)
                                                    episode_buffer = []
                                                    sess.run(self.update_local_ops)

                                                if d and self.restarting is False:
                                                    # print("break by d", d)
                                                    self.restarting = True
                                                    break                                         
                        
                                self.episode_rewards.append(episode_reward)
                                self.episode_lengths.append(episode_step_count)
                                self.episode_mean_values.append(np.mean(episode_values))

                                # Update the network using the experience buffer at the end of the episode.
                                if training and len(episode_buffer) != 0:
                                    v_l, p_l, e_l, loss_f, g_n, v_n = self.train(episode_buffer, sess, gamma, 0.0)

                                # Periodically save gifs of episodes, model parameters, and summary statistics.
                                if episode_count % 5 == 0 and episode_count != 0:
                                    if training and episode_count % 50 == 0 and self.name == 'worker_0':
                                        time_per_step = 0.05
                                        images = np.array(episode_frames)
                                        # images = np.array(np.delete(episode_frames,obj=3, axis=3))
                                        make_gif(images, './frames/image' + str(episode_count) +'_reward_' + str(episode_reward) + '.gif',
                                                    duration=len(images) * time_per_step, true_image=True, salience=False)
                                    if training and episode_count % 5 == 0 and self.name == 'worker_0':
                                        saver.save(sess, self.model_path + '/model-' + str(episode_count) + '.ckpt')
                                        # print("Saved Model")

                                    mean_reward = np.mean(self.episode_rewards[-5:])  # mean over the last 5 elements of episode Rs
                                    mean_length = np.mean(self.episode_lengths[-5:])
                                    mean_value = np.mean(self.episode_mean_values[-5:])

                                    summary = tf.Summary()
                                    summary.value.add(tag='Performance/Reward', simple_value=float(mean_reward))
                                    summary.value.add(tag='Performance/Length', simple_value=float(mean_length))
                                    summary.value.add(tag='Performance/Value', simple_value=float(mean_value))
                                    if training:
                                        summary.value.add(tag='Losses/Value Loss', simple_value=float(v_l))
                                        summary.value.add(tag='Losses/Policy Loss', simple_value=float(p_l))
                                        summary.value.add(tag='Losses/Entropy', simple_value=float(e_l))
                                        summary.value.add(tag='Losses/Grad Norm', simple_value=float(g_n))
                                        summary.value.add(tag='Losses/Var Norm', simple_value=float(v_n))
                                        summary.value.add(tag='Losses/Loss', simple_value=float(loss_f))
                                        self.summary_writer_train.add_summary(summary, episode_count)
                                        self.summary_writer_train.flush()
                                    else:
                                        self.summary_writer_play.add_summary(summary, episode_count)
                                        self.summary_writer_play.flush()

                                if self.name == 'worker_0':
                                    sess.run(self.increment)
                                episode_count += 1
                    except:
                        pass
                    
                    

def initialize_variables(saver, sess, load_model):
    if load_model:
        # print('Loading Model...')
        ckpt = tf.train.get_checkpoint_state(model_path)
        saver.restore(sess, ckpt.model_checkpoint_path)
    else:
        sess.run(tf.global_variables_initializer())


def play_training(training=True, load_model=True):
    # Session create for road segmentation
    # rs_sess, rs_input_tensor, rs_output_tensor = model_init()
    screen = Screen()

    with tf.device("/cpu:0"):
        global_episodes = tf.Variable(0, dtype=tf.int32, name='global_episodes', trainable=False)
        # trainer = tf.train.RMSPropOptimizer(learning_rate=1e-4, decay=0.99, epsilon=1)
        trainer = tf.train.AdamOptimizer(learning_rate=1e-4)
        master_network = AC_Network(s_size, a_size, 'global', None, False)
	
        worker_ips = [
                '165.132.108.169'#,
                # '192.168.0.2',
                # '192.168.0.3',
                # '192.168.0.4',
                # '192.168.0.5',
        ]

        # worker_maps = [
        #     'Hockenheim_Short',
        #     'California_Highway_3',
        #     'Brands_Hatch_Indy',
        #     'Nurburgring_Sprint',
        #     'OultonPark_Island'
        # ]

        worker_maps = [
            # 'California_Highway_3',
            'California_Highway_3',
            'California_Highway_3',
            'California_Highway_3',
            'California_Highway_3'
        ]

        if training:
            #num_workers = multiprocessing.cpu_count()  # Set workers at number of available CPU threads
            num_workers = len(worker_ips)
        else:
            num_workers = len(worker_ips)

        workers = []
        for i in range(num_workers):
            workers.append(
                # Worker(PcarsEnv(vision=True, throttle=False, gear_change=False, port=3101 + i), i, s_size, a_size,
                #        trainer, model_path, global_episodes, False))
                Worker(PcarsEnv(worker_maps[i]), i, s_size, a_size,
                       trainer, model_path, global_episodes, False))
        saver = tf.train.Saver()

    with tf.Session() as sess:
        coord = tf.train.Coordinator()
        initialize_variables(saver, sess, load_model)
        # Asynchronous magic happens: start the "work" process for each worker in a separate thread.
        worker_threads = []
        for i, worker in enumerate(workers):
            worker_work = lambda: worker.work(max_episode_length, gamma, sess, coord, saver, training, worker_ips[i], screen)
            t = threading.Thread(target=worker_work)
            t.start()
            sleep(0.5)
            worker_threads.append(t)
        coord.join(worker_threads)  # waits until the specified threads have stopped.

if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-l', '--loadmodel', dest='load_model', type=bool,
    #                     default=False, help='Score threshold for displaying bounding boxes')
    
    max_episode_length = 300
    gamma = .99  # discount rate for advantage estimation and reward discounting
    s_size = 90000#340464  # Observations are greyscale frames of 84 * 84 * 1
    a_size = 31  # Left, Right, Forward, Brake
    model_path = './model'

    tf.reset_default_graph()

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    # Create a directory to save episode playback gifs to
    if not os.path.exists('./frames'):
        os.makedirs('./frames')

    if len(sys.argv) == 1:  # run from PyCharm
        play_training(training=True, load_model=False)
    elif sys.argv[1] == "1":  # lunch from Terminal and specify 0 or 1 as arguments
        play_training(training=True, load_model=False)
    elif sys.argv[1] == "2":  # lunch from Terminal and specify 0 or 1 as arguments
        play_training(training=True, load_model=True)
    elif sys.argv[1] == "0":
        play_training(training=False, load_model=True)
