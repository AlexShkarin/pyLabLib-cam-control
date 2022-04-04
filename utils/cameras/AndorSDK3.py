from pylablib.devices import Andor
from pylablib.thread.devices.Andor import AndorSDK3CameraThread, AndorSDK3ZylaThread

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI



class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def _add_attribute(self, name, attribute, value):
        if not attribute.readable:
            return
        indicator=not attribute.writable
        if attribute.kind=="int":
            self._record_attribute(name,"int",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_integer_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="float":
            self._record_attribute(name,"float",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_float_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="enum":
            if attribute.values:
                self._record_attribute(name,"enum",attribute,indicator=indicator,rng=attribute.ilabels)
                self.add_choice_parameter(name,attribute.name,attribute.ilabels,indicator=indicator)
        elif attribute.kind=="str":
            self._record_attribute(name,"str",attribute,indicator=indicator)
            self.add_string_parameter(name,attribute.name,indicator=indicator)
        elif attribute.kind=="bool":
            self._record_attribute(name,"bool",attribute,indicator=indicator)
            self.add_bool_parameter(name,attribute.name,indicator=indicator)
    def _get_attribute_range(self, attribute):
        if attribute.kind in ["int","float"]:
            return (attribute.min,attribute.max)
        if attribute.kind=="enum":
            return attribute.ilabels

class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")

class StatusZyla_GUI(GenericCameraStatus_GUI):
    def setup_status_table(self):
        self.add_num_label("buffer_overflows",formatter="int",label="Buffer overflows:")
        self.add_num_label("temperature_monitor",formatter=("float","auto",1,True),label="Temperature (C):")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "temperature_monitor" in params:
            self.v["temperature_monitor"]=params["temperature_monitor"]
        if "missed_frames" in params:
            self.v["buffer_overflows"]=params["missed_frames"].overflows




class AndorSDK3CameraDescriptor(ICameraDescriptor):
    _cam_kind="AndorSDK3"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Andor SDK3 cameras")
        try:
            cam_num=Andor.get_cameras_number_SDK3()
        except (Andor.AndorError, OSError):
            if verbose: print("Error loading or running the Andor SDK3 library: required software (Andor Solis) must be missing\n")
            return
        if not cam_num:
            if verbose: print("Found no Andor SDK3 cameras\n")
            return
        if verbose: print("Found {} Andor SDK3 camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i in range(cam_num):
            try:
                if verbose: print("Found Andor SDK3 camera idx={}".format(i))
                with Andor.AndorSDK3Camera(idx=i) as cam:
                    device_info=cam.get_device_info()
                    if verbose: print("\tModel {}".format(device_info.camera_model))
                    yield cam,None
            except Andor.AndorError:
                pass
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        device_info=cam.get_device_info()
        cam_desc=cls.build_cam_desc(params={"idx":idx})
        cam_desc["display_name"]="Andor {} {}".format(device_info.camera_model,device_info.serial_number)
        cam_name="andor_sdk3_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Generic Andor SDK3"
    
    def make_thread(self, name):
        return AndorSDK3CameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)




class AndorSDK3ZylaCameraDescriptor(AndorSDK3CameraDescriptor):
    _cam_kind="AndorSDK3Zyla"
    _expands="AndorSDK3"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if cam.get_device_info().camera_model.lower().startswith("zyla"):
            return super().generate_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "Andor Zyla"
    def make_thread(self, name):
        return AndorSDK3ZylaThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_status(self, parent):
        return StatusZyla_GUI(parent,cam_desc=self)