from ScopeFoundry import HardwareComponent
import csv
from ScopeFoundry.logged_quantity import LoggedQuantity
import os
import threading
import time


dtype_map = dict(Integer=int, FloatingPoint=float, Boolean=bool, Command=None, Enumerated=str, String=str )


class Andor3CameraHW(HardwareComponent):
    
    name = 'andor3_camera'

    def setup(self):
        
        self.add_operation('Test', self.test_func)
        os.chdir(r'C:\Users\lab\Documents\foundry_scope\ScopeFoundryHW\andor3')

        self.feature_dict = feature_dict = dict()
        with open('feature_list.csv', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for row in reader:
                print(row)
                key, type_ = row
                type_ = type_.strip()
                
                feature_dict[key] = dict(name=key, type=type_, dtype=dtype_map[type_])
        

        #print(feature_dict)


        for x in self.feature_dict.keys():
            A = feature_dict[x]
            if A['type'] == 'Command':
                continue

            choices = None
            if A['type'] == 'Enumerated':
                choices = ()
            lq = self.settings.New(A['name'], dtype=A['dtype'], choices=choices)
            A['lq'] = lq
        
        

    def connect(self):
        
        from pyAndorSDK3 import AndorSDK3
        
        print ("Connecting to camera")
        
        self.sdk3 = AndorSDK3()
        self.cam = cam = self.sdk3.GetCamera(0)
        #print (cam.SerialNumber)        
        debug = self.settings['debug_mode']
    
        #self.settings.temperature.connect_to_hardware(read_func= lambda cam=cam: cam.SensorTemperature)
        
        #print(cam.SensorTemperature) 
        
        for x in self.feature_dict.keys():
            A = self.feature_dict[x]

            #print("="*10, A['name'])
            A['implemented'] = self.hw_feature_is_implemented(A['name'])
            
            if not A['implemented']:
                A['lq'].change_readonly(True)
                continue

            
            A['readable'] = self.hw_feature_is_readable(A['name'])
            A['writable'] = self.hw_feature_is_writable(A['name'])
            A['readonly'] = self.hw_feature_is_readonly(A['name'])
            
            if debug:
                print(x, A)
            

            
            if A['type'] == 'Command':
                continue

            if A['type'] == 'Enumerated':
                A['lq'].change_choice_list(tuple(self.hw_feature_enum_options(A['name'])))
            A['lq'].change_readonly(A['readonly'])
            
            read_func = None
            if A['readable']:
                read_func = lambda n=A['name']: self.hw_feature_read(n)
            write_func = None
            if A['writable']:
                write_func = lambda x, n=A['name']: self.hw_feature_write(n, x)
            
            A['lq'].connect_to_hardware(read_func = read_func,
                                        write_func = write_func)

        #turn on cooling and keep reading it
        self.settings['SensorCooling']=True
        self.update_thread_interrupted = False
        self.update_thread = threading.Thread(target=self.update_thread_run, daemon=True)        
        self.update_thread.start()

        self.read_from_hardware()
        
    def hw_feature_is_implemented(self, feature_name):
        return bool(self.cam._lib.is_implemented(self.cam._handle,feature_name))
    
    def hw_feature_is_readable(self, feature_name):
        return bool(self.cam._lib.is_readable(self.cam._handle, feature_name ))
    def hw_feature_is_writable(self, feature_name):
        return bool(self.cam._lib.is_readable(self.cam._handle, feature_name ))    
        
    def hw_feature_is_readonly(self, feature_name):
        return bool(self.cam._lib.is_readonly(self.cam._handle,feature_name))
        
    def hw_feature_write(self, feature_name, value):
        self.cam.__setattr__(feature_name, value)
        
    def hw_feature_read(self, feature_name):
        return self.cam.__getattr__(feature_name)
        
    def hw_feature_enum_options(self, feature_name):
        return self.cam.__getattr__("options_" + feature_name)

    def update_thread_run(self):
        while not self.update_thread_interrupted:
            self.settings.SensorTemperature.read_from_hardware()
            self.settings.TemperatureStatus.read_from_hardware()
            time.sleep(1)
        
    
    def disconnect(self):
        self.update_thread_interrupted = True
        self.settings.disconnect_all_from_hardware()
        
        if hasattr(self, 'cam'):
            self.cam.close()
            del self.cam
            
        if hasattr(self, 'sdk3'):
            self.sdk3._lib.finalise()
            del self.sdk3

            
            
    def test_func(self):
        
        print("TEST")
        
        print(self.cam.TemperatureControl)