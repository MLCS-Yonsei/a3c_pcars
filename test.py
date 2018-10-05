from control import *
from control.matlab import *
import matplotlib.pyplot as plt 
import numpy as np
from datetime import datetime

zeta = 0.707
w0 = 1
ts = 0.01

t1 = datetime.now()
g = tf(w0*w0, [1,2*zeta,w0*w0])
gz = c2d(g,ts)

coeffs = tfdata(gz)

co = {
    'a1':coeffs[1][0][0][1],
    'a2':coeffs[1][0][0][2],
    'b1':coeffs[0][0][0][0],
    'b2':coeffs[0][0][0][1],
    'dt':gz.dt
}


theta_k_2 = 0.8
theta_k_1 = 0.78

u_k_2 = 0.9
u_k_1 = 0.8

theta_k = co['a1'] * theta_k_1 + co['a2'] * theta_k_2 + co['b1'] * u_k_1 + co['b2'] * u_k_2

print(gz)
print(co)
print(theta_k)

t2 = datetime.now()
print(t2-t1)

# t = np.arange(0, 16, 0.1)
# y,t1 = step(gz,t)
# plt.step(t,y)
# plt.grid()
# plt.xlabel('t') 
# plt.ylabel('y')
# plt.show()