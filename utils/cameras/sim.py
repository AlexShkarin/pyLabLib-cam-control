from pylablib.devices.interface import camera
from pylablib.thread.devices.generic.camera import GenericCameraThread

from .base import ICameraDescriptor
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI

import time
import collections
import numpy as np


TDeviceInfo=collections.namedtuple("TDeviceInfo",["kind"])
class SimulatedCamera(camera.IROICamera, camera.IExposureCamera):
    """
    Generic simulated camera.

    Allows settings exposure (equal to frame rate), ROI, and frame buffer.

    Args:
        size: full "sensor" size
    """
    def __init__(self, size=(1024,1024)):
        super().__init__()
        self._size=size
        self._roi=(0,size[0],0,size[1])
        self._exposure=.1
        self._opened=False
        self._acquistion_started=None
        self.open()
        self._add_info_variable("device_info",self.get_device_info)
        
    def open(self):
        self._opened=True
    def close(self):
        if self._opened:
            self.clear_acquisition()
        self._opened=False
    def is_opened(self):
        return self._opened
    def _get_connection_parameters(self):
        return (self._size,)

    def get_device_info(self):
        return TDeviceInfo("simulated_basic",)
    
    ### Generic controls ###
    _min_exposure=1E-3
    def get_frame_timings(self):
        return self._TAcqTimings(self._exposure,self._exposure)
    @camera.acqstopped
    def set_exposure(self, exposure):
        self._exposure=max(exposure,self._min_exposure)
        return self._exposure

    ### Acquisition process controls ###
    def setup_acquisition(self, nframes=100):  # pylint: disable=arguments-differ
        super().setup_acquisition(nframes=nframes)
    def clear_acquisition(self):
        self.stop_acquisition()
        super().clear_acquisition()
    def start_acquisition(self, *args, **kwargs):
        self.stop_acquisition()
        super().start_acquisition(*args,**kwargs)
        self._acquistion_started=time.time()
        self._frame_counter.reset(self._acq_params["nframes"])
    def stop_acquisition(self):
        if self.acquisition_in_progress():
            self._frame_counter.update_acquired_frames(self._get_acquired_frames())
            self._acquistion_started=None
    def acquisition_in_progress(self):
        return self._acquistion_started is not None
    def get_frames_status(self):
        if self.acquisition_in_progress():
            self._frame_counter.update_acquired_frames(self._get_acquired_frames())
        return self._TFramesStatus(*self._frame_counter.get_frames_status())
    def _get_acquired_frames(self):
        if self._acquistion_started is None:
            return None
        return int((time.time()-self._acquistion_started)//self._exposure)

    ### Image settings and transfer controls ###
    def get_detector_size(self):
        return self._size
    def get_roi(self):
        return self._roi
    @camera.acqcleared
    def set_roi(self, hstart=0, hend=None, vstart=0, vend=None):
        hlim,vlim=self.get_roi_limits()
        hstart,hend=self._truncate_roi_axis((hstart,hend),hlim)
        vstart,vend=self._truncate_roi_axis((vstart,vend),vlim)
        self._roi=(hstart,hend,vstart,vend)
        return self.get_roi()
    def get_roi_limits(self, hbin=1, vbin=1):
        wdet,hdet=self.get_detector_size()
        hlim=camera.TAxisROILimit(1,wdet,1,1,1)
        vlim=camera.TAxisROILimit(1,hdet,1,1,1)
        return hlim,vlim

    def _get_data_dimensions_rc(self):
        roi=self.get_roi()
        return (roi[3]-roi[2]),(roi[1]-roi[0])
    _support_chunks=True
    def _get_base_frame(self):
        """Generate the base static noise-free frame"""
        xs,ys=np.meshgrid(np.arange(self._size[0]),np.arange(self._size[1]),indexing="ij")
        ip,jp=self._size[0]/2,self._size[1]/2
        iw,jw=self._size[0]/10,self._size[0]/20
        mag=1024
        return np.exp(-(xs-ip)**2/(2*iw**2)-(ys-jp)**2/(2*jw**2))*mag
    def _read_frames(self, rng, return_info=False):
        c0,c1,r0,r1=self._roi
        base=self._get_base_frame()[r0:r1,c0:c1].astype(self._default_image_dtype)
        return [base+np.random.randint(0,256,size=(rng[1]-rng[0],)+base.shape,dtype=self._default_image_dtype)],None



class SimulatedCameraThread(GenericCameraThread):
    """Device thread for a simulated camera"""
    parameter_variables=GenericCameraThread.parameter_variables|{"exposure","frame_period","detector_size","buffer_size","acq_status","roi_limits","roi"}
    def connect_device(self):
        self.device=SimulatedCamera(size=self.cam_size)
    def setup_task(self, size=(1024,1024), remote=None, misc=None):  # pylint: disable=arguments-differ
        self.cam_size=size
        super().setup_task(remote=remote,misc=misc)




class SimulatedCameraDescriptor(ICameraDescriptor):
    _cam_kind="simulated"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        yield from []  # do not discover by default
    
    def get_kind_name(self):
        return "Simulated camera"
    
    def make_thread(self, name):
        return SimulatedCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return GenericCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)