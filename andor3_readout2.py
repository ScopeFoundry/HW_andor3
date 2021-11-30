import numpy as np
import time
import pyqtgraph as pg
import queue
import os
import imageio

from ScopeFoundry import Measurement 

#import matplotlib.gridspec as gridspec 
from time import sleep

from ScopeFoundry import h5_io
from ScopeFoundry.helper_funcs import load_qt_ui_file, sibling_path

# ROW0 = 240
# ROW1 = 271
# 
# 
# 
# def pixel2wavelength(grating_position, pixel_index, binning = 1):
#     # Wavelength calibration based off of work on 4/30/2014
#     # changed 3/20/2015 after apd alignement offset = -5.2646 #nm
#     offset = -4.2810
#     focal_length = 293.50 #mm
#     delta = 0.0704  #radians
#     gamma = 0.6222  # radian
#     grating_spacing = 1/150.  #mm
#     pixel_size = 16e-3  #mm   #Binning!
#     m_order = 1 #diffraction order
# 
#     wl_center = (grating_position + offset)*1e-6
#     px_from_center = pixel_index*binning +binning/2. - 256
#     
#     psi = np.arcsin(m_order* wl_center / (2*grating_spacing*np.cos(gamma/2)))
#     
#     eta = np.arctan(px_from_center*pixel_size*np.cos(delta) /
#     (focal_length+px_from_center*pixel_size*np.sin(delta)))
#     
#     return 1e6*((grating_spacing/m_order)
#                     *(np.sin(psi-0.5*gamma)
#                       + np.sin(psi+0.5*gamma+eta)))



class Andor3ReadoutMeasure(Measurement):

    name = "andor3_readout"
    
    def setup(self):
        
        self.display_update_period = 0.050 #seconds

        #local logged quantities
        self.bg_subtract = self.settings.New('bg_subtract', dtype=bool, initial=False, ro=False)
        self.acquire_bg  = self.settings.New('acquire_bg',  dtype=bool, initial=False, ro=False)

        self.settings.New('continuous', dtype=bool, initial=True, ro=False) 
        self.settings.New('save_h5', dtype=bool, initial=True)

        self.settings.New('wl_calib', dtype=str, initial='pixels', choices=('pixels','raw_pixels','acton_spectrometer', 'andor_spectrometer'))
        self.settings.New("upper_vbin_limit", dtype=int,initial=2159,ro=False)
        self.settings.upper_vbin_limit.add_listener(self.set_upper_vbin_limLine)
        self.settings.New("lower_vbin_limit", dtype=int,initial=0,ro=False)
        self.settings.lower_vbin_limit.add_listener(self.set_lower_vbin_limLine)

        self.add_operation('run_acquire_bg', self.acquire_bg_start)
        self.add_operation('run_acquire_single', self.acquire_single_start)

        self.settings.New('show_line', bool, initial=False)
        
        
#     def pixel2wavelength(self, grating_position, pixel_index):
#         offset = self.settings['calib_offset'] # nm
#         focal_length = self.settings['calib_focal_length'] # mm
#         delta = self.settings['calib_delta'] # rad
#         gamma = self.settings['calib_gamma'] #rad
#         grating_spacing = 1./self.settings['calib_grating_groves']  #mm
#         pixel_size = self.settings['calib_pixel_size']*1e-3  #mm   #Binning!
#         m_order = self.settings['calib_m_order'] #diffraction order
#         
#         ccd_hw = self.app.hardware['andor_ccd']
#         binning_yx = ccd_hw.settings['ccd_shape']/ ccd_hw.settings['readout_shape']
#         binning = binning_yx[1]
#             
#         wl_center = (grating_position + offset)*1e-6
#         px_from_center = pixel_index*binning +binning/2. - 0.5*ccd_hw.settings['ccd_shape'][1]
#         
#         psi = np.arcsin(m_order* wl_center / (2*grating_spacing*np.cos(gamma/2)))
#         
#         eta = np.arctan(px_from_center*pixel_size*np.cos(delta) /
#         (focal_length+px_from_center*pixel_size*np.sin(delta)))
#         
#         return 1e6*((grating_spacing/m_order)
#                         *(np.sin(psi-0.5*gamma)
#                           + np.sin(psi+0.5*gamma+eta)))        
    
    def acquire_bg_start(self):
        self.settings.continuous.update_value(False)
        self.acquire_bg.update_value(True)
        self.start()
    
    def acquire_single_start(self):
        self.settings.continuous.update_value(False)
        self.start()

    def setup_figure(self):

        #if hasattr(self, 'graph_layout'):
        #    self.graph_layout.deleteLater() # see http://stackoverflow.com/questions/9899409/pyside-removing-a-widget-from-a-layout
        #    del self.graph_layout
            
        ui = self.ui = load_qt_ui_file(sibling_path(__file__, 'andor3_cmos_readout.ui'))
        
        ## ui connection
        self.hw = andor = self.app.hardware['andor3_camera']
#       self.hw_spectro=self.app.hardware['andor_spec']
        andor.settings.connected.connect_to_widget(ui.hw_connect_checkBox)
        andor.settings.ExposureTime.connect_to_widget_one_way(ui.ExposureTime_doubleSpinBox)
        ui.ExposureTime_doubleSpinBox.valueChanged.connect(lambda: self.changeAcqOpt('ExposureTime'))
        andor.settings.SensorTemperature.connect_to_widget(ui.temperature_doubleSpinBox)
        #andor.settings.AccumulateCount.connect_to_widget_one_way(ui.Acc_Num_doubleSpinBox)
        #ui.Acc_Num_doubleSpinBox.valueChanged.connect(lambda: self.changeAcqOpt('AccumulateCount'))
        #ui.Acc_Num_doubleSpinBox.valueChanged.connect(lambda: self.changeAcqOpt('FrameCount'))
        andor.settings.TemperatureStatus.connect_to_widget(ui.temp_status_comboBox)
               
        #self.settings.bg_subtract.connect_to_widget(ui.andor_ccd_bgsub_checkBox)
    
        ui.acq_bg_pushButton.clicked.connect(self.acquire_bg_start)
        ui.andor_ccd_start_pushButton.clicked.connect(self.acquire_to_save)
        ui.andor_ccd_interrupt_pushButton.clicked.connect(self.interrupt)
        ui.andor_ccd_run_pushButton.clicked.connect(self.run_continuously)
        self.settings.progress.connect_to_widget(self.ui.acquisition_progressBar)
        #ui.andor_ccd_read_single_pushButton.clicked.connect(self.acquire_single_start)
        
        #andor.settings.TemperatureStatus.connect_to_widget(self.ui.temp_status_label)
        andor.settings.TargetSensorTemperature.connect_to_widget(self.ui.temp_setpoint_doubleSpinBox)
        
        #self.settings.save_h5.connect_to_widget(self.ui.save_h5_checkBox)
        
        #andor.settings.connected.connect_to_widget(self.ui.hw_connect_checkBox)
        
        #self.settings.wl_calib.connect_to_widget(self.ui.wl_calib_comboBox)

#        self.hw_spectro.settings.grating_id.connect_to_widget(self.ui.gratings_comboBox)
#        self.hw_spectro.settings.input_flipper.connect_to_widget(self.ui.Spectro_in_ComboBox)
#        self.hw_spectro.settings.output_flipper.connect_to_widget(self.ui.Spectro_out_ComboBox)
#        self.hw_spectro.settings.center_wl.connect_to_widget(self.ui.center_wl)
        

        #### PLot window
        # NOTE, view toggling is handled in andor_ccd_readout.ui file!!
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.spec_plot = self.graph_layout.addPlot()
        self.spec_plot_line = self.spec_plot.plot([1,3,2,4,3,5])
        self.spec_plot.enableAutoRange()
        
        ## measure_line
        self.spec_infline = pg.InfiniteLine(movable=True, angle=90, label='x={value:0.2f}', 
                       labelOpts={'position':0.1, 'color': (200,200,100), 'fill': (200,200,200,50), 'movable': True})
        self.settings.show_line.add_listener(self.on_change_show_line)
        self.settings.show_line.connect_to_widget(self.ui.show_spec_line_checkBox)
        
        #### Image window        
        self.img_graphlayout = pg.GraphicsLayoutWidget()
        self.ui.image_groupBox.layout().addWidget(self.img_graphlayout)
        self.img_plot = self.img_graphlayout.addPlot()
        #self.img_plot.getViewBox().setLimits(minXRange=-10, maxXRange=100, minYRange=-10, maxYRange=100)
        self.img_plot.showGrid(x=True, y=True)
        self.img_plot.setAspectLocked(lock=True, ratio=1)
        self.img_item = pg.ImageItem()
        self.img_plot.addItem(self.img_item)
        self.hist_lut = pg.HistogramLUTItem()
        self.hist_lut.autoHistogramRange()
        self.hist_lut.setImageItem(self.img_item)
        self.img_graphlayout.addItem(self.hist_lut)

        #set the horizontal lines in the plot for binning
        self.lower_vbin_limLine=pg.InfiniteLine(pos=0, angle=0,movable=True, bounds=[0,2159])
        self.lower_vbin_limLine.addMarker('<|')
        self.img_plot.addItem(self.lower_vbin_limLine)
        self.lower_vbin_limLine.sigPositionChanged.connect(self.set_lower_vbin_limit)
        
        self.upper_vbin_limLine=pg.InfiniteLine(pos=2159, angle=0,movable=True,bounds=[0,2159])
        self.upper_vbin_limLine.addMarker('|>')
        self.img_plot.addItem(self.upper_vbin_limLine)
        self.upper_vbin_limLine.sigPositionChanged.connect(self.set_upper_vbin_limit)


        
        self.cam_controls = self.app.hardware['andor3_camera'].settings.New_UI(style='scroll_form')
        self.ui.camera_settings_GroupBox.layout().addWidget(self.cam_controls)

#         
#         
#         self.graph_layout = pg.GraphicsLayoutWidget()
#         self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
#         
#         self.spec_plot = self.graph_layout.addPlot()
#         self.spec_plot_line = self.spec_plot.plot([1,3,2,4,3,5])
#         self.spec_plot.enableAutoRange()
#         self.spec_infline = pg.InfiniteLine(movable=True, angle=90, label='x={value:0.2f}', 
#                        labelOpts={'position':0.1, 'color': (200,200,100), 'fill': (200,200,200,50), 'movable': True})
#         self.spec_plot.addItem(self.spec_infline)
# 
#         
#         
#         self.graph_layout.nextRow()
#         
#         self.img_plot = self.graph_layout.addPlot()
#         #self.img_plot.getViewBox().setLimits(minXRange=-10, maxXRange=100, minYRange=-10, maxYRange=100)
#         self.img_plot.showGrid(x=True, y=True)
#         self.img_plot.setAspectLocked(lock=True, ratio=1)
#         self.img_item = pg.ImageItem()
#         self.img_plot.addItem(self.img_item)
# 
# 
#         self.hist_lut = pg.HistogramLUTItem()
#         self.hist_lut.autoHistogramRange()
#         self.hist_lut.setImageItem(self.img_item)
#         self.graph_layout.addItem(self.hist_lut)
        
    def set_lower_vbin_limit(self):
        self.settings["lower_vbin_limit"]=int(self.lower_vbin_limLine.getPos()[1])
        
    def set_upper_vbin_limit(self):
        self.settings["upper_vbin_limit"]=int(self.upper_vbin_limLine.getPos()[1])
    
    def set_lower_vbin_limLine(self):
        if hasattr(self, 'lower_vbin_limLine'):
            self.lower_vbin_limLine.setPos(self.settings["lower_vbin_limit"])
        
    def set_upper_vbin_limLine(self):
        if hasattr(self, 'upper_vbin_limLine'):
            self.upper_vbin_limLine.setPos(self.settings["upper_vbin_limit"])

    def on_change_show_line(self):
        if self.settings['show_line']:
            self.spec_plot.addItem(self.spec_infline)
        else:
            self.spec_plot.removeItem(self.spec_infline)
        

    def run(self):
        self.settings['progress']=0
        try:
            #setup data arrays         
            
            camera_hw = self.app.hardware['andor3_camera']
            self.cam = cam = camera_hw.cam

            cam.CycleMode = "Fixed"
            self.AqcOptBuffer = queue.Queue()

            while not self.interrupt_measurement_called:
                

                #calculate the x-axis for spectra
                wl_calib = self.settings['wl_calib']
                hbin = 1 #ccd_dev.get_current_hbin()
                width_px = 2560
                
                if wl_calib=='acton_spectrometer':
                    px_index = np.arange(width_px)
                    spec_hw = self.app.hardware['acton_spectrometer']
                    self.wls = spec_hw.get_wl_calibration(px_index, hbin)
                elif wl_calib=='andor_spectrometer':
                    px_index = np.arange(width_px)
                    spec_hw = self.app.hardware['andor_spec']
                    self.wls = spec_hw.get_wl_calibration(px_index, hbin)   
                elif wl_calib=='pixels':
                    binning = hbin
                    px_index = np.arange(width_px)
                    self.wls = binned_px = binning*px_index + 0.5*(binning-1)
                elif wl_calib=='raw_pixels':
                    self.wls = np.arange(width_px)
                else:
                    self.wls = np.arange(width_px)
                
                #check if the exposure was ment to be changed during acquisition. if so, change it now.
                while self.AqcOptBuffer.empty()==False:
                    AcqOpt=self.AqcOptBuffer.get()
                    self.hw.settings[AcqOpt[0]]=AcqOpt[1]

                #the acquire function is copied from the andor_camera.py and then and idle loop is insertet while waiting for the buffer. this listens for a measurment interrupt and keeps track of progress
                #if not cam._lib.get_bool(cam._handle, "CameraAcquiring"):
                def acquire( loop_progress,accumulations,*args, **kwargs,):
                    cam.configure(*args)
                    timeout = kwargs.pop('timeout', max(5000, np.ceil(5 * 1000 / cam.FrameRate)))
                    min_buf = kwargs.pop('min_buf', 2)
                    pause_after = kwargs.pop('pause_after', 0.0)
                    sw_trigger = cam.TriggerMode == "SoftwareTrigger"
                    for _ in range(0, min_buf):
                        cam._queue_buffer(cam.ImageSizeBytes)
                    try:
                        cam.AcquisitionStart()
                        if sw_trigger : cam.SoftwareTrigger()

                        #idle loop here
                        if cam.ExposureTime>0.1:
                            acq_start=time.time()
                            time_progressed=0
                            while time_progressed<cam.ExposureTime:
                                if self.interrupt_measurement_called:
                                    self.cam.AcquisitionInterrupt()
                                    break

                                self.settings['progress']=(loop_progress/accum+(time_progressed/cam.ExposureTime/accum))*100
                                time.sleep(0.05)
                                time_progressed=time.time()-acq_start

                        acq = cam._acquire(timeout)
                    except Exception as e:
                        cam.AcquisitionStop()
                        cam._flush()
                        raise e
                    if(pause_after > 0):
                        time.sleep(pause_after)
                    cam.AcquisitionStop()
                    cam._flush()
                    return acq


                #setup the accumulation then start the actual data acquisition
                accum=int(self.ui.Acc_Num_doubleSpinBox.value())
                im_buff=np.zeros((camera_hw.settings['SensorHeight'],camera_hw.settings['SensorWidth']),dtype=np.uint64)
                for k in range(accum):

                    if self.interrupt_measurement_called: break
                    im_buff+=acquire(k,accum,frame_count=1, timeout=20000).image.copy()

                    self.im=im_buff/(k+1)
                    upper_vbin_limit=int(self.upper_vbin_limLine.getPos()[1])
                    lower_vbin_limit=int(self.lower_vbin_limLine.getPos()[1])
                    self.spectra_data=np.sum(self.im[lower_vbin_limit:upper_vbin_limit,:],axis=0)

                
                if not self.settings['continuous']: #stop the loop when not running contiuously
                    break
                
            while self.AqcOptBuffer.empty()==False:
                    AcqOpt=self.AqcOptBuffer.get()
                    self.hw.settings[AcqOpt[0]]=AcqOpt[1]
        finally:
        # Save data file if the measurement wasnt interrupted

            

            if self.settings['save_h5']:
                if not self.interrupt_measurement_called:

                    #make sure to get latest data (save function might be called before the actual refresh of the plot happens so dont take it from there)
                    save_img=np.fliplr(self.im) #flip left right to have same orientation as in the display function
                    #buit H5 file
                    self.t0 = time.time()
                    self.h5_file = h5_io.h5_base_file(self.app, measurement=self )
                    self.h5_file.attrs['time_id'] = self.t0
                    H = self.h5_meas_group  =  h5_io.h5_create_measurement_group(self, self.h5_file)
                    
                    #create h5 data arrays
                    H['image'] = save_img
                    
                    self.h5_file.close()

                    #also save as tiff file. Note that we have to convert to integer and normlize for the 16bit format of tiff files if the counts/pixel exceed that limitation (should not occur since accumulate uses averaging)
                    tiff_data= np.array(save_img/np.amax(save_img)*65536).astype(np.uint16)

                    
                    t = time.localtime(time.time())
                    t_string = "{:02d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(int(str(t[0])[2:4]), t[1], t[2], t[3], t[4], t[5])
                    fname = os.path.join(self.app.settings['save_dir'], "%s_%s_%s" % (t_string,self.app.settings.sample.val, self.name))
                    im = np.arange(100,dtype=np.uint16).reshape(10,10)
                    imageio.imwrite(fname + '.tif',tiff_data)
            
 

    def run_continuously(self):
        self.settings['continuous']=True
        self.settings['save_h5']=False
        self.start()

    def acquire_to_save(self):
        self.settings['continuous']=False
        self.settings['save_h5']=True
        self.start()

    def changeAcqOpt(self,Opt):
        cam = self.app.hardware['andor3_camera'].cam
        if cam._lib.get_bool(cam._handle, "CameraAcquiring"):
            self.AqcOptBuffer.put([Opt,self.sender().value()])
        else:
            self.hw.settings[Opt]=self.sender().value()

    
    def update_display(self):
        if hasattr(self, 'im'):
            #print('update_display', self.buffer_.shape)
            if len(self.im.shape) == 2:
                self.img_item.setImage(np.rot90(self.im.T,2), autoLevels=False)
                self.hist_lut.imageChanged(autoLevel=True, autoRange=True)
                y = self.spectra_data
                
            else: # kinetic
                self.img_item.setImage(self.buffer_[:,:,:].sum(axis=0).astype(np.float32).T, autoLevels=False)
                self.hist_lut.imageChanged(autoLevel=True, autoRange=True)
                y = self.buffer_[:,:,:].sum(axis=(0,1))

            x = self.wls        
            self.spec_plot_line.setData(x,y)
    
    def get_spectrum(self):
        return np.squeeze(self.spectrum)
    
    def get_wavelengths(self):
        return self.wls