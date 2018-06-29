import pandas as pd
import numpy as np


df = pd.read_csv('output.csv',sep=',',header=None)
data = df.values #(4537,76)


lapDistance = []
for k in range(19):
    for i in range(len(data)):
        lapDistance.append(int(data[i][4*k]))

unique_lapDistance = list(set(lapDistance))

minLap = min(lapDistance)
maxLap = max(lapDistance)

results = np.empty([19,maxLap,3],dtype = object)

for k in range(19):
    lapDistance = []
    for i in range(len(data)):
        lapDistance.append(int(data[i][4*k]))

    position = np.empty([len(data)],dtype = object)
    for i in range(len(data)):
        if data[i][4*k] != 0:
            position[i] = data[i][1+(4*k):4+(4*k)]

    result = np.empty([maxLap-minLap],dtype = object)
    lapDistance = np.asarray(lapDistance)
    
    for i in range(maxLap):
        if i in unique_lapDistance:
            if i == 0:
                a = np.empty((3,))
                a[:] = 0
                results[k][i] = a
            elif i > 0:    
                idxes = np.where(lapDistance==i)[0]
                
                idxes = idxes.tolist()
                
                positions = position[idxes]
                if len(positions) > 0:
                    avg = np.mean(positions)
                    results[k][i] = avg
                else:

                    a = np.empty((3,))
                    a[:] = np.nan
                    results[k][i] = a
        else:
            a = np.empty((3,))
            a[:] = 0
            results[k][i] = a

results = np.transpose(results, (1,0,2))

results = np.nanmean(results,axis=1)

np.savez_compressed('grid_line',results=results)

