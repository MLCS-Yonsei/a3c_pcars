# send_crest_request
import http.client
import csv 
import json
import os.path

import threading
import datetime
#import redis

def send_crest_requset(url, flag, option):
    global standaloneWriter
    conn = http.client.HTTPConnection(url)
    conn.request("GET", "/crest/v1/api")

    res = conn.getresponse()
    data = json.loads(res.read().decode('utf8', "ignore"))
    if data["gameStates"]["mGameState"] > 1:
        if flag == 'standalone':
            file_path = './standalone.csv'

            with open(file_path, 'a') as f:
                writer = csv.writer(f)
                writer.writerow([str(datetime.now()),data])
        elif flag == 'crest-monitor':
            return data
        
    return data

