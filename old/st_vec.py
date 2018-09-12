from numpy import linalg as LA
import numpy as np
import math

m = 15
v_range = [-1,1]
g = 0.7

v = np.linspace(v_range[0], v_range[1], num=m).tolist()

b = []
for _v in v:
    # _b = (math.pi / 2)* _v*(1-g) / (g - 2 * g * abs(_v) + 1)
    _b =  _v*(1-g) / (g - 2 * g * LA.norm(v, ord=2) + 1)
    b.append(_b)

x = []
t = 0
for i, _b in enumerate(b):
    if i<(m-1)/2:
        # print(_b)
        t+=_b

t2=0

result = []
for i, _b in enumerate(b):
    b[i] = (_b * 1 / t)
    _r = 0
    if i<(m-1)/2:
        for j in range(i,int((m-1)/2)):
            _r += b[j] 
    elif i>(m-1)/2:
        for j in range(i,(m)):
            _r += b[j] 
    result.append(_r)

print(result)
# print(t)
# print(b)
# print(x)