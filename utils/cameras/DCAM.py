from pylablib.devices import DCAM
from pylablib.thread.devices.DCAM import DCAMCameraThread

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI




class DCAMOrcaCameraThread(DCAMCameraThread):
    parameter_variables=DCAMCameraThread.parameter_variables|{"defect_correct_mode"}

class DCAMImagEMCameraThread(DCAMCameraThread):
    def _apply_additional_parameters(self, parameters):
        super()._apply_additional_parameters(parameters)
        if "sensitivity" in parameters:
            self.device.cav["SENSITIVITY"]=parameters["sensitivity"]
    def _update_additional_parameters(self, parameters):
        parameters["sensitivity"]=self.device.cav["SENSITIVITY"]
        return super()._update_additional_parameters(parameters)


class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def _add_attribute(self, name, attribute, value):
        indicator=not attribute.writable
        if attribute.kind=="int":
            self._record_attribute(name,"int",attribute,indicator=indicator)
            self.add_integer_parameter(name,attribute.name,limits=(attribute.min,attribute.max),default=attribute.default,indicator=indicator)
        elif attribute.kind=="float":
            self._record_attribute(name,"float",attribute,indicator=indicator)
            self.add_float_parameter(name,attribute.name,limits=(attribute.min,attribute.max),default=attribute.default,indicator=indicator)
        elif attribute.kind=="enum":
            self._record_attribute(name,"enum",attribute,indicator=indicator)
            self.add_choice_parameter(name,attribute.name,attribute.ilabels,indicator=indicator)



class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="same"
    _frame_period_kind="indicator"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.EnumGUIParameter(self,"readout_speed","Readout speed",{"slow":"Slow","normal":"Normal","fast":"Fast"}),"advanced")
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")

class OrcaSettings_GUI(Settings_GUI):
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.BoolGUIParameter(self,"defect_correct_mode","Defect correction",default=True),"advanced",row=-2)

class ImagEMSettings_GUI(Settings_GUI):
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.IntGUIParameter(self,"sensitivity","EMCCD sensitivity",(0,255)),"advanced",row=-2)







class DCAMCameraDescriptor(ICameraDescriptor):
    _cam_kind="DCAM"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for DCAM cameras")
        try:
            cam_num=DCAM.get_cameras_number()
        except (DCAM.DCAMError, OSError):
            if verbose: print("Error loading or running the DCAM library: required software (Hamamtsu HOKAWO or DCAM API) must be missing\n")
            return
        if cam_num==0:
            if verbose: print("Found no DCAM cameras\n")
            return
        if verbose: print("Found {} DCAM camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i in range(cam_num):
            try:
                if verbose: print("Found DCAM camera idx={}".format(i))
                with DCAM.DCAMCamera(idx=i) as cam:
                    device_info=cam.get_device_info()
                    if verbose: print("\tVendor {}, model {}".format(device_info.vendor,device_info.model))
                    yield cam,None
            except DCAM.DCAMError:
                pass
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        device_info=cam.get_device_info()
        cam_desc=cls.build_cam_desc(params={"idx":idx})
        cam_desc["display_name"]="{} {}".format(device_info.model,device_info.serial_number)
        cam_name="dcam_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Generic Hamamatsu"
    
    def make_thread(self, name):
        return DCAMCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)




class DCAMOrcaCameraDescriptor(DCAMCameraDescriptor):
    _cam_kind="DCAMOrca"
    _expands="DCAM"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if cam.get_device_info().model.lower().startswith("c11440"):
            return super().generate_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "Hamamatsu Orca"
    def make_thread(self, name):
        return DCAMOrcaCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return OrcaSettings_GUI(parent,cam_desc=self)


class DCAMImagEMCameraDescriptor(DCAMCameraDescriptor):
    _cam_kind="DCAMImagEM"
    _expands="DCAM"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if cam.get_device_info().model.lower().startswith("c9100"):
            return super().generate_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "Hamamatsu ImagEM"
    def make_thread(self, name):
        return DCAMImagEMCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return ImagEMSettings_GUI(parent,cam_desc=self)