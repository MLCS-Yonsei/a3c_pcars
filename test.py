import pandas as pd
import numpy as np

df = pd.read_csv('output.csv',sep=',',header=None)
data = df.values #(4537,76)

results = []
lapDistance = []
for k in range(19):
    for i in range(len(data)):
        lapDistance.append(int(data[i][4*k]))

minLap = min(lapDistance)
maxLap = max(lapDistance)

for k in range(19):
    lapDistance = []
    for i in range(len(data)):
        lapDistance.append(int(data[i][4*k]))

    position = np.empty([len(lapDistance)],dtype = object)
    for i in range(len(data)):
        if data[i][4*k] != 0:
            position[i] = data[i][1+(4*k):4+(4*k)]


    result = np.empty([maxLap-minLap],dtype = object)
    lapDistance = np.asarray(lapDistance)
#     index = np.where(lapDistance==3)[0]
#     index = index.tolist()
#     positions = position[index]
#     if positions != 0:
#         result[k] = np.mean(positions)

#     else: 
#         result[k] = np.array([0,0,0])
#     print(result[k])
#     results.append(result)
# results =np.vstack(results)


    for i in range(maxLap):
        if i in lapDistance:
            idxes = np.where(lapDistance==i+1)[0]
            idxes = idxes.tolist()
            positions = position[idxes]
            if positions is not None:
                avg = np.mean(positions)
                result[i] = avg
                # print(positions.shape)
            else:
                result[i] = True#np.array([0,0,0])
        else:
            result[i] = True#np.array([0,0,0])


    print(result.shape)
    results.append(result)

results = np.vstack(results)
np.savez_compressed('results',a=results)
print(results.shape)
results = np.mean(results,axis=0)
np.savez_compressed('position',a=results)
print(results.shape)
