import numpy as np
import time
import pyqtgraph as pg

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


        self.add_operation('run_acquire_bg', self.acquire_bg_start)
        self.add_operation('run_acquire_single', self.acquire_single_start)

        
        
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
            
        ui = self.ui = load_qt_ui_file(sibling_path(__file__, 'andor3_readout.ui'))
        
        ## ui connection
        self.hw = andor = self.app.hardware['andor3_camera']
        andor.settings.connected.connect_to_widget(ui.hw_connect_checkBox)
        andor.settings.exposure_time.connect_to_widget(ui.andor_ccd_int_time_doubleSpinBox)
        andor.settings.temperature.connect_to_widget(ui.andor_ccd_temp_doubleSpinBox)
        andor.settings.camera_status.connect_to_widget(ui.andor_ccd_status_label)
               
        #self.settings.bg_subtract.connect_to_widget(ui.andor_ccd_bgsub_checkBox)
    
        self.settings.continuous.connect_to_widget(ui.andor_ccd_acquire_cont_checkBox)
        ui.andor_ccd_acq_bg_pushButton.clicked.connect(self.acquire_bg_start)
        #ui.andor_ccd_read_single_pushButton.clicked.connect(self.acquire_single_start)
        
        #andor.settings.temp_status.connect_to_widget(self.ui.temp_status_label)
        andor.settings.temp_setpoint.connect_to_widget(self.ui.temp_setpoint_doubleSpinBox)
        
        #self.settings.save_h5.connect_to_widget(self.ui.save_h5_checkBox)
        
        #andor.settings.connected.connect_to_widget(self.ui.hw_connect_checkBox)
        
        #self.settings.wl_calib.connect_to_widget(self.ui.wl_calib_comboBox)
        

        #### PLot window
        
        import pyqtgraph.dockarea as dockarea

        self.dockarea = dockarea.DockArea()
        self.ui.plot_groupBox.layout().addWidget(self.dockarea)
        
        self.spec_plot = pg.PlotWidget()
        spec_dock = self.dockarea.addDock(name='Spec', position='below', widget=self.spec_plot)
        self.spec_plot_line = self.spec_plot.plot([1,3,2,4,3,5])
        self.spec_plot.enableAutoRange()

        self.img_graphlayout = pg.GraphicsLayoutWidget()
        self.img_plot = self.img_graphlayout.addPlot()
        self.img_item = pg.ImageItem()
        self.img_plot.addItem(self.img_item)
        self.img_plot.showGrid(x=True, y=True)
        self.img_plot.setAspectLocked(lock=True, ratio=1)
        self.dockarea.addDock(name='Img', position='below', relativeTo=spec_dock, widget=self.img_graphlayout)
        
        self.lower_vbin_lim=pg.InfiniteLine(pos=0, angle=0,movable=True, bounds=[0,2159])
        self.lower_vbin_lim.addMarker('<|')
        self.img_plot.addItem(self.lower_vbin_lim)
        self.upper_vbin_lim=pg.InfiniteLine(pos=2159, angle=0,movable=True,bounds=[0,2159])
        self.upper_vbin_lim.addMarker('|>')
        self.img_plot.addItem(self.upper_vbin_lim)
        


        self.hist_lut = pg.HistogramLUTItem()
        self.hist_lut.autoHistogramRange()
        self.hist_lut.setImageItem(self.img_item)
        self.img_graphlayout.addItem(self.hist_lut)
        
        self.cam_controls = self.app.hardware['andor3_camera'].settings.New_UI(style='scroll_form')
        self.dockarea.addDock(name='Settings', position='below', relativeTo=spec_dock, widget=self.cam_controls)

        spec_dock.raiseDock()

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
        


    def run(self):
        #setup data arrays         
        
        camera_hw = self.app.hardware['andor3_camera']
        cam = camera_hw.cam
        #width_px = ccd_dev.Nx_ro
        #height_px = ccd_dev.Ny_ro
        
        #ccd_hw.settings['acq_mode'] = 'single'
        #camera_hw.settings['trigger_mode'] = 'internal'
        
        cam.CycleMode = "Fixed"
        
        
        while not self.interrupt_measurement_called:

            acq = cam.acquire(frame_count=1, timeout=20000)
            
            self.im = acq.image.copy()
            upper_vbin_limit=int(self.upper_vbin_lim.getPos()[1])
            lower_vbin_limit=int(self.lower_vbin_lim.getPos()[1])
            self.spectra_data =np.sum(self.im[lower_vbin_limit:upper_vbin_limit,:],axis=0)
            print(acq.image)
            
            
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
                
            if not self.settings['continuous']:
                break


        # Ensure you have write permission for the destination location
        #acq.show()
       # t_acq = self.app.hardware['andor_ccd'].settings['exposure_time'] #in seconds
        
       #wait_time = 0.01 #np.min(1.0,np.max(0.05*t_acq, 0.05)) # limit update period to 50ms (in ms) or as slow as 1sec
        
        # print('andor_ccd_readout run')
        
        '''   
        try:
            self.log.info("starting acq")
            
            # print("starting acq")
            ccd_dev.start_acquisition()
        
            self.log.info( "checking..." )
            t0 = time.time()

#             if 'acton_spectrometer' in self.app.hardware and self.app.hardware['acton_spectrometer'].settings['connected']:
#                 self.wls  = self.pixel2wavelength(
#                               self.app.hardware['acton_spectrometer'].settings['center_wl'], 
#                               np.arange(width_px))
#                               #, binning=ccd_dev.get_current_hbin())
#             else:
#                 self.wls = np.arange(width_px)

            while not self.interrupt_measurement_called:

                wl_calib = self.settings['wl_calib']
                hbin = ccd_dev.get_current_hbin()
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

            
                stat = ccd_hw.settings.ccd_status.read_from_hardware()
                if stat == 'IDLE':
                    # grab data
                    t1 = time.time()
                    #print "acq time", (t1-t0)
                    t0 = t1
                
                    self.buffer_ = ccd_hw.get_acquired_data()
                                        
                    #print('andor_ccd buffer', self.buffer_.shape, ccd_dev.buffer.shape)
                
                    if self.bg_subtract.val and not self.acquire_bg.val:
                        bg = ccd_hw.background
                        if bg is not None:
                            if bg.shape == self.buffer_.shape:
                                self.buffer_ = self.buffer_ - bg
                            else:
                                self.log.warning("Background not the correct shape {} != {}".format( self.buffer_.shape, bg.shape))
                        else:
                            self.log.warning( "No Background available, raw data shown")
                            
                    if ccd_hw.settings['acq_mode'] == 'accumulate':
                        self.buffer_ = self.buffer_ / ccd_hw.settings['num_acc']

                    self.spectra_data = np.average(self.buffer_, axis=0)
 
 
                    if self.acquire_bg.val or not self.settings.continuous.val:
                        break # end the while loop for non-continuous scans
                    else:
                        # restart acq
                        ccd_dev.start_acquisition()
                    
                else:
                    #sleep(wait_time)
                    #print("GetTotalNumberImagesAcquired", ccd_dev.get_total_number_images_acquired())
                    #print("get_number_new_images", ccd_dev.get_number_new_images())
                    #print("get_number_available_images", ccd_dev.get_number_available_images())
                    sleep(0.01)
                    try:
                        ccd_hw.settings.temperature.read_from_hardware()
                        ccd_hw.settings.temp_status.read_from_hardware()
                    except Exception as err:
                        pass # sometimes temperature can't be read during acquisition
        #except Exception as err:
        #    self.log.error( "{} error: {}".format(self.name, err))
        finally:            
            # while-loop is complete
            ccd_hw.interrupt_acquisition()

            
            #is this right place to put this?
            # Signal emission from other threads ok?
            #self.measurement_state_changed.emit(False)
        
            if self.acquire_bg.val:
                if self.interrupt_measurement_called:
                    ccd_hw.background = None
                else:
                    ccd_hw.background = self.buffer_.copy()
                self.acquire_bg.update_value(False)    
        
            if not self.settings.continuous.val:
                if self.interrupt_measurement_called:
                    self.spectrum = None
                else:
                    self.spectrum = self.buffer_.copy()
                    
                # Save data file
                if self.settings['save_h5']:
                    self.t0 = time.time()
                    self.h5_file = h5_io.h5_base_file(self.app, measurement=self )
                    self.h5_file.attrs['time_id'] = self.t0
                    H = self.h5_meas_group  =  h5_io.h5_create_measurement_group(self, self.h5_file)
                
                    #create h5 data arrays
                    H['wls'] = self.wls
                    H['spectrum'] = self.spectrum
                
                    self.h5_file.close()

                # NPZ data file
                if False: 
                    save_dict = {
                             'spectrum': self.spectrum,
                             'wls': self.wls,
                                }               
                    
                    for lqname,lq in self.app.settings.as_dict().items():
                        save_dict[lqname] = lq.val
                    for hw in self.app.hardware.values():
                        for lqname,lq in hw.settings.as_dict().items():
                            save_dict[hw.name + "_" + lqname] = lq.val
                    for lqname,lq in self.settings.as_dict().items():
                        save_dict[self.name +"_"+ lqname] = lq.val
    
                    self.fname = "%i_%s.npz" % (time.time(), self.name)
                    np.savez_compressed(self.fname, **save_dict)
                    self.log.info( "saved: " + self.fname)
                    
                self.log.info( "Andor CCD single acq successfully acquired")
                # print("Andor CCD single acq successfully acquired")
                # self.settings.continuous.update_value(True)
                
            ccd_hw.settings.ccd_status.read_from_hardware()
            ccd_hw.settings.temperature.read_from_hardware()
            ccd_hw.settings.temp_status.read_from_hardware()
        '''
        
    
    def update_display(self):
        if hasattr(self, 'im'):
            #print('update_display', self.buffer_.shape)
            if len(self.im.shape) == 2:
                self.img_item.setImage(self.im.T, autoLevels=False)
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