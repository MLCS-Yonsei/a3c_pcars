import mss
import mss.tools
import numpy as np
# import cv2
import win32ui
import win32gui

# The simplest use, save a screen shot of the 1st monitor
class ImageCapture():
    def __init__(self):
        self.img = None

    def get_img(self):
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "Project CARS™" ))
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        with mss.mss() as sct:
            # The screen part to capture
            monitor = {'top': y, 'left': x, 'width': w, 'height': h}

            # Grab the data
            self.img = np.asarray(sct.grab(monitor))[:,:,:3]
            
        return self.img