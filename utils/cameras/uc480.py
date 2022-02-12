from pylablib.devices import uc480
from pylablib.thread.devices.uc480 import UC480CameraThread
from pylablib.core.utils import dictionary

from .base import ICameraDescriptor
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI
from ..gui import cam_gui_parameters



class PixelRateFloatGUIParameter(cam_gui_parameters.FloatGUIParameter):
    """
    Pixel rate parameter.

    Same as the basic floating point parameter, but automatically updates limits upon setup.
    """
    def __init__(self, settings, indicator=False, cam_name=None, cam_range_name=None):
        super().__init__(settings,"pixel_rate","Pixel rate (MHz)",limit=(0,None),indicator=indicator,factor=1E-6,cam_name=cam_name)
        self.cam_range_name=cam_range_name
    def setup(self, parameters, full_info):
        super().setup(parameters,full_info)
        if self.cam_range_name is not None and self.cam_range_name in full_info:
            rmin,rmax=full_info[self.cam_range_name][:2]
            self.base.w[self.gui_name].set_limiter((rmin*self.factor,rmax*self.factor))


class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"
    def get_basic_parameters(self, name):
        if name=="pixel_rate": return PixelRateFloatGUIParameter(self,cam_range_name="pixel_rates_range")
        return super().get_basic_parameters(name)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_builtin_parameter("pixel_rate","advanced")

class Status_GUI(GenericCameraStatus_GUI):
    def setup_status_table(self):
        self.add_num_label("frames_lost",formatter=("int"),label="Frames lost:")
    def show_parameters(self, params):
        super().show_parameters(params)
        if "acq_status" in params:
            self.v["frames_lost"]=params["acq_status"].transfer_missed




class UC480CameraDescriptor(ICameraDescriptor):
    _cam_kind="UC480"
    _backend_names={"uc480":"Throlabs uc480","ueye":"IDS uEye"}
    _backend_software={"uc480":"ThorCam","ueye":"IDS uEye"}

    @classmethod
    def _detect_backend(cls, backend, verbose=False):
        if verbose: print("Searching for {} cameras".format(cls._backend_names[backend]))
        cameras=dictionary.Dictionary()
        try:
            cam_infos=uc480.list_cameras(backend=backend)
        except (uc480.uc480Error, OSError):
            if verbose: print("Error loading or running {} library: required software ({}) must be missing\n".format(
                    backend,cls._backend_software[backend]))
            return cameras
        cam_num=len(cam_infos)
        if not cam_num:
            if verbose: print("Found no {} cameras\n".format(backend))
            return cameras
        if verbose: print("Found {} {} camera{}".format(cam_num,backend,"s" if cam_num>1 else ""))
        for c in cam_infos:
            idx=c.cam_id
            dev_idx=c.dev_id
            sn=c.serial_number
            if verbose: print("Found {} camera dev_idx={}, cam_idx={}".format(backend,dev_idx,idx))
            if verbose: print("\tModel {}, serial {}".format(c.model,sn))
            cam_desc=cls.build_cam_desc(params={"idx":idx,"dev_idx":dev_idx,"sn":sn,"backend":backend})
            cam_desc["display_name"]="{} {}".format(c.model,c.serial_number)
            cam_name="{}_{}".format(backend,idx)
            cameras[cam_name]=cam_desc
            if verbose: cls.print_added_camera(cam_name,cam_desc)
        return cameras
    @classmethod
    def detect(cls, verbose=False):
        cameras=dictionary.Dictionary()
        cameras.update(cls._detect_backend("uc480",verbose=verbose))
        cameras.update(cls._detect_backend("ueye",verbose=verbose))
        return cameras
    
    def get_kind_name(self):
        return self._backend_names[self.settings.get("params/backend","uc480")]
    
    def make_thread(self, name):
        return UC480CameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return Status_GUI(parent,cam_desc=self)