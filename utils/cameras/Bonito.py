from pylablib.devices import IMAQ
from pylablib.devices.AlliedVision import Bonito
from pylablib.thread.devices.AlliedVision import IMAQBonitoCameraThread
from pylablib.core.thread import controller

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI





class BlackOffsetParameter(cam_gui_parameters.IGUIParameter):
    def add(self, base):
        self.base=base
        self.base.add_check_box("change_bl_offset","Change black level offset",False,add_indicator=False)
        self.base.add_num_edit("bl_offset",value=0,limiter=(0,None,"coerce","int"),formatter="int",label="Black level offset")
        self.base.vs["change_bl_offset"].connect(controller.exsafe(lambda v: self.base.set_enabled("bl_offset",v)))
        self.base.set_enabled("bl_offset",False)
        self.connect_updater(["bl_offset","change_bl_offset"])
    def _update_value(self, v):
        if self.base.v["change_bl_offset"]:
            super()._update_value(v)
    def collect(self, parameters):
        if self.base.v["change_bl_offset"]:
            parameters["bl_offset"]=self.base.v["bl_offset"]
        return super().collect(parameters)
    def display(self, parameters):
        if "bl_offset" in parameters:
            self.base.i["bl_offset"]=parameters["bl_offset"]
        return super().display(parameters)


class BonitoCameraSettings_GUI(GenericCameraSettings_GUI):
    _roi_kind="minsize"
    def get_basic_parameters(self, name):
        """Get basic GUI parameters, which can be shared between different cameras"""
        if name=="exposure": return cam_gui_parameters.FloatGUIParameter(self,"exposure","Exposure (ms)",limit=(0,None),fmt=".4f",default=100,factor=1E3)
        if name=="frame_period": return cam_gui_parameters.FloatGUIParameter(self,"frame_period","Frame period (ms)",limit=(0,None),fmt=".4f",default=0,factor=1E3)
        if name=="roi": return cam_gui_parameters.ROIGUIParameter(self,bin_kind=self._bin_kind,roi_kind=self._roi_kind)
        if name=="bl_offset": return BlackOffsetParameter(self)
        if name=="status_line": return cam_gui_parameters.BoolGUIParameter(self,"status_line","Status line",default=True)
        if name=="perform_status_check": return cam_gui_parameters.BoolGUIParameter(self,"perform_status_check","Perform status line check",default=True,add_indicator=False,indirect=True)
        return super().get_basic_parameters(name)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_builtin_parameter("bl_offset","advanced")
        self.add_builtin_parameter("status_line","advanced").allow_diff_update=True
        self.add_builtin_parameter("perform_status_check","advanced").allow_diff_update=True
        self.advanced_params.vs["status_line"].connect(controller.exsafe(lambda v: self.advanced_params.set_enabled("perform_status_check",v)))
    def collect_parameters(self):
        parameters=super().collect_parameters()
        parameters["perform_status_check"]&=parameters["status_line"]
        return parameters



class BonitoIMAQCameraDescriptor(ICameraDescriptor):
    _cam_kind="BonitoIMAQ"
    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for IMAQ Bonito cameras")
        try:
            imaq_cams=IMAQ.list_cameras()
        except (IMAQ.IMAQError, OSError):
            if verbose: print("Error loading or running the IMAQ library: required software (NI Vision) must be missing\n")
            if verbose=="full": cls.print_error()
            return
        cam_num=len(imaq_cams)
        if not cam_num:
            if verbose: print("Found no IMAQ cameras\n")
            return
        if verbose: print("Found {} IMAQ camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for name in imaq_cams:
            try:
                if verbose: print("Found IMAQ camera {}".format(name))
                with IMAQ.IMAQCamera(name) as cam:
                    if not Bonito.check_grabber_association(cam):
                        continue
                yield None,name
            except IMAQ.IMAQError:
                if verbose=="full": cls.print_error()
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        imaq_name=info
        with Bonito.BonitoIMAQCamera(imaq_name=imaq_name) as cam:
            device_info=cam.get_device_info()
            cam_desc=cls.build_cam_desc(params={"imaq_name":imaq_name})
            cam_desc["display_name"]=device_info.version.splitlines()[0]
            cam_name="allvis_bonito_imaq_{}".format(idx)
        return cam_name,cam_desc
    def get_kind_name(self):
        return "Bonito + IMAQ"
    def make_thread(self, name):
        return IMAQBonitoCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return BonitoCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)