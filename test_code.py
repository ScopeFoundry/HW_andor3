import logging

logging.basicConfig(level=logging.ERROR)

#logger = logging.getLogger('mylogger')
#logger.setLevel(logging.DEBUG)

#from andor3 import Andor3
#cam = Andor3()

from pyAndorSDK3 import AndorSDK3

print ("Connecting to camera")

sdk3 = AndorSDK3()
cam = sdk3.GetCamera(0)
print (cam.SerialNumber)