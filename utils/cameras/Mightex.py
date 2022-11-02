from pylablib.devices import Mightex
from pylablib.thread.devices.Mightex import MightexSSeriesCameraThread

from .base import ICameraDescriptor
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI




class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="same"


class MightexSSeriesCameraDescriptor(ICameraDescriptor):
    _cam_kind="MightexSSeries"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Mightex cameras")
        try:
            cams=Mightex.list_cameras_s()
        except (Mightex.MightexError, OSError, AttributeError):
            if verbose: print("Error loading or running the Mightex S Series library: required software must be missing\n")
            if verbose=="full": cls.print_error()
            return
        if len(cams)==0:
            if verbose: print("Found no Mightex cameras\n")
            return
        cam_num=len(cams)
        if verbose: print("Found {} Mightex camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i,cdesc in enumerate(cams):
            if verbose: print("Checking Mightex camera idx={}\n\Model {},   serial {}".format(i,cdesc.model,cdesc.serial))
            yield None,cdesc
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        cam_desc=cls.build_cam_desc(params={"idx":info.idx})
        cam_desc["display_name"]="{} {}".format(info.model,info.serial)
        cam_name="mightex_sseries_{}".format(idx)
        return cam_name,cam_desc

    def get_kind_name(self):
        return "Generic Mightex S Series"
    def make_thread(self, name):
        return MightexSSeriesCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)