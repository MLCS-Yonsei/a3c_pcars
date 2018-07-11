import win32gui
import win32ui 
windowname = "Project CARS™"
bmpfilenamename = "123.bmp"
hwnd = win32gui.FindWindow(None, windowname)

l, t, _r, b = win32gui.GetWindowRect(hwnd)

target_w = 800
target_h = 600

margin_w  = int((_r-l-target_w) / 2)

l = l + margin_w
_r = _r - margin_w
b = b - margin_w
t = t + ((b-t-target_h))
w = _r - l
h = b - t

wDC = win32gui.GetWindowDC(hwnd)
dcObj=win32ui.CreateDCFromHandle(wDC)
cDC=dcObj.CreateCompatibleDC()
dataBitMap = win32ui.CreateBitmap()
dataBitMap.CreateCompatibleBitmap(dcObj, w, h)
cDC.SelectObject(dataBitMap)
cDC.BitBlt((0,0),(w, h) , dcObj, (0,0), win32con.SRCCOPY)
dataBitMap.SaveBitmapFile(cDC, bmpfilenamename)
# Free Resources
dcObj.DeleteDC()
cDC.DeleteDC()
win32gui.ReleaseDC(hwnd, wDC)
win32gui.DeleteObject(dataBitMap.GetHandle())