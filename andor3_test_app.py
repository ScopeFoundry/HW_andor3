from ScopeFoundry import BaseMicroscopeApp
#from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file

class Andor3TestApp(BaseMicroscopeApp):

    name = 'andor3_test'
    
    def setup(self):
        
        from ScopeFoundryHW.andor3.andor3_hw import Andor3CameraHW
        self.add_hardware(Andor3CameraHW(self))
        
        from ScopeFoundryHW.andor3.andor3_readout2 import Andor3ReadoutMeasure
        self.add_measurement(Andor3ReadoutMeasure)

if __name__ == '__main__':
    import sys
    app = Andor3TestApp(sys.argv)
    sys.exit(app.exec_())