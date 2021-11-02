from ctypes import c_int, c_uint, c_byte, c_ubyte, c_short, c_double, c_float, c_long
from ctypes import pointer, byref, windll, cdll


HANDLES = dict(
    AT_HANDLE_UNINITIALISED=-1,
    AT_HANDLE_SYSTEM=1
    )



class AndorCamera(object):
    
    def __init__(self, debug=False):
        
        if debug:
            print("Andor Camera __init__")
        
        andorlibpath = r"C:\Program Files\Andor SDK3\atcore.dll"
        
        A = self.andorlib = cdll.LoadLibrary(andorlibpath)
        
        print(self.andorlib)
        
        A.AT_InitialiseLibrary()
        
        
        n = c_int(-543)
        A.AT_GetInt(HANDLES['AT_HANDLE_SYSTEM'], "Device Count", byref(n))
        print(n, n.value)
    
    
    
    def get_int(self, ):
        pass
    
    
    def close(self):
        self.andorlib.AT_FinaliseLibrary()
        
        
if __name__ == '__main__':

    a = AndorCamera(debug=True)
    a.close()
    
    