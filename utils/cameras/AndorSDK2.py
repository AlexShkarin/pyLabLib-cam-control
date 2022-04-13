from pylablib.devices import Andor
from pylablib.thread.devices.Andor import AndorSDK2CameraThread, AndorSDK2LucaThread, AndorSDK2IXONThread

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI



class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"

class AdvancedCameraSettings_GUI(Settings_GUI):
    _hsspeeds=["10 MHz","5 MHz","3 MHz","1 MHz"]
    _vsspeeds=["0.3 us","0.5 us","0.9 us","1.7 us","3.3 us"]
    _preamps=["1","2.5","5.1"]
    _temp_params=(None,None,None)
    def get_basic_parameters(self, name):
        if name=="shutter":return cam_gui_parameters.EnumGUIParameter(self,"shutter","Shutter",
            {"open":"Opened","closed":"Closed","auto":"Auto"},default="closed",from_camera=lambda v: v[0])
        if name=="frame_transfer": return cam_gui_parameters.BoolGUIParameter(self,"frame_transfer","Frame transfer mode")
        if name=="hsspeed": return cam_gui_parameters.EnumGUIParameter(self,"hsspeed","Horizontal shift speed",self._hsspeeds)
        if name=="vsspeed": return cam_gui_parameters.EnumGUIParameter(self,"vsspeed","Vertical shift period",self._vsspeeds)
        if name=="preamp": return cam_gui_parameters.EnumGUIParameter(self,"preamp","Preamp gain",self._preamps)
        if name=="EMCCD_gain": return cam_gui_parameters.IntGUIParameter(self,"EMCCD_gain","EMCCD gain",limit=(0,255),
            to_camera=lambda v: (v,False), from_camera=lambda v:v[0])
        if name=="fan_mode": return cam_gui_parameters.EnumGUIParameter(self,"fan_mode","Fan",{"off":"Off","low":"Low","full":"Full"})
        if name=="cooler": return cam_gui_parameters.EnumGUIParameter(self,"cooler","Cooler",{9:"off",1:"On"},default=1)
        if name=="temperature": return cam_gui_parameters.IntGUIParameter(self,"temperature","Temperature (C)",
            limit=self._temp_params[:2],default=self._temp_params[2])
        return super().get_basic_parameters(name)

class IXONCameraSettings_GUI(AdvancedCameraSettings_GUI):
    _temp_params=(-120,30,-100)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_builtin_parameter("shutter","common",row=0)
        self.add_builtin_parameter("frame_transfer","advanced")
        self.add_builtin_parameter("hsspeed","advanced")
        self.add_builtin_parameter("vsspeed","advanced")
        self.add_builtin_parameter("preamp","advanced")
        self.add_builtin_parameter("EMCCD_gain","advanced")
        self.add_builtin_parameter("fan_mode","advanced")
        self.add_builtin_parameter("cooler","advanced")
        self.add_builtin_parameter("temperature","advanced")

class LucaCameraSettings_GUI(AdvancedCameraSettings_GUI):
    _temp_params=(-40,30,-20)
    def get_basic_parameters(self, name):
        if name=="fan_mode": return cam_gui_parameters.EnumGUIParameter(self,"fan_mode","Fan",{"off":"Off","full":"Full"})
        return super().get_basic_parameters(name)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_builtin_parameter("frame_transfer","advanced")
        self.add_builtin_parameter("EMCCD_gain","advanced")
        self.add_builtin_parameter("fan_mode","advanced")
        self.add_builtin_parameter("cooler","advanced")
        self.add_builtin_parameter("temperature","advanced")




class IXONCameraStatus_GUI(GenericCameraStatus_GUI):
    def setup_status_table(self):
        self.add_text_label("temperature_status",label="Temperature status:")
        self.add_num_label("temperature_monitor",formatter=("float","auto",1,True),label="Temperature (C):")
    def show_parameters(self, params):
        super().show_parameters(params)
        if "temperature_monitor" in params:
            self.v["temperature_monitor"]=params["temperature_monitor"]
        temp_status_text={"off":"Cooler off","not_reached":"Approaching...","not_stabilized":"Stabilizing...","drifted":"Drifted","stabilized":"Stable"}
        if "temperature_status" in params:
            self.v["temperature_status"]=temp_status_text[params["temperature_status"]]

LucaCameraStatus_GUI=IXONCameraStatus_GUI






class AndorSDK2CameraDescriptor(ICameraDescriptor):
    _cam_kind="AndorSDK2"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Andor SDK2 cameras")
        try:
            cam_num=Andor.get_cameras_number_SDK2()
        except (Andor.AndorError, OSError):
            if verbose: print("Error loading or running the Andor SDK2 library: required software (Andor Solis) must be missing\n")
            if verbose=="full": cls.print_error()
            return
        if not cam_num:
            if verbose: print("Found no Andor SDK2 cameras\n")
            return
        if verbose: print("Found {} Andor SDK2 camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i in range(cam_num):
            try:
                if verbose: print("Found Andor SDK2 camera idx={}".format(i))
                with Andor.AndorSDK2Camera(idx=i) as cam:
                    device_info=cam.get_device_info()
                    if verbose: print("\tModel {}".format(device_info.head_model))
                    yield cam,None
            except Andor.AndorError:
                if verbose=="full": cls.print_error()
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        device_info=cam.get_device_info()
        cam_desc=cls.build_cam_desc(params={"idx":idx})
        cam_desc["display_name"]="Andor {} {}".format(device_info.head_model,device_info.serial_number)
        cam_name="andor_sdk2_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Generic Andor SDK2"
    
    def make_thread(self, name):
        return AndorSDK2CameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)



class AndorSDK2IXONCameraDescriptor(AndorSDK2CameraDescriptor):
    _cam_kind="AndorSDK2IXON"
    _expands="AndorSDK2"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if cam.get_capabilities()["cam_type"]=="AC_CAMERATYPE_IXON":
            return super().generate_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "Andor iXON"
    def make_thread(self, name):
        return AndorSDK2IXONThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return IXONCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return IXONCameraStatus_GUI(parent,cam_desc=self)



class AndorSDK2LucaCameraDescriptor(AndorSDK2CameraDescriptor):
    _cam_kind="AndorSDK2Luca"
    _expands="AndorSDK2"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if cam.get_capabilities()["cam_type"]=="AC_CAMERATYPE_LUCA":
            return super().generate_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "Andor Luca"
    def make_thread(self, name):
        return AndorSDK2LucaThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return LucaCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return LucaCameraStatus_GUI(parent,cam_desc=self)