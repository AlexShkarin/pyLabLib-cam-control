from pylablib.devices import Photometrics
from pylablib.thread.devices.Photometrics import PvcamCameraThread
from pylablib.core.utils import dictionary

from .base import ICameraDescriptor
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI
from ..gui import cam_gui_parameters



class TriggerModeParameter(cam_gui_parameters.IGUIParameter):
    """
    PVCam trigger mode parameter.
    
    Receives possible values from the camera.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.disabled=False
    def add(self, base):
        self.base=base
        base.add_combo_box("trigger_mode",label="Trigger mode",options=["Internal"],index_values=[None],location={"indicator":"next_line"})
        base.add_combo_box("trigger_out_mode",label="Trigger out",options=["None"],index_values=[None],location={"indicator":"next_line"})
        self.connect_updater(["trigger_mode","trigger_out_mode"])
    def setup(self, parameters, full_info):
        super().setup(parameters,full_info)
        if "parameter_ranges/trigger_mode" in full_info:
            trig_modes,trig_out_modes=full_info["parameter_ranges/trigger_mode"]
            index_values=list(trig_modes)
            self.base.w["trigger_mode"].set_options([trig_modes[v] for v in index_values],index_values=index_values,value=index_values[0])
            index_values=list(trig_out_modes)
            self.base.w["trigger_out_mode"].set_options([trig_out_modes[v] for v in index_values],index_values=index_values,value=index_values[0])
            if index_values==[None]:
                self.base.set_enabled("trigger_out_mode",False)
        else:
            self.disabled=True
            self.base.set_enabled(["trigger_mode","trigger_out_mode"],False)
    def collect(self, parameters):
        if not self.disabled:
            parameters["trigger_mode"]=self.base.v["trigger_mode"],self.base.v["trigger_out_mode"]
        return super().collect(parameters)
    def display(self, parameters):
        if "trigger_mode" in parameters and not self.disabled:
            self.base.i["trigger_mode"],self.base.i["trigger_out_mode"]=parameters["trigger_mode"]
        return super().display(parameters)

class ClearModeParameter(cam_gui_parameters.EnumGUIParameter):
    """
    PVCam clear mode parameter.
    
    Receives possible values from the camera.
    """
    def __init__(self, settings):
        super().__init__(settings,"clear_mode","Clear mode",{None:"None"})
        self.add_indicator="next_line"
    def setup(self, parameters, full_info):
        super().setup(parameters,full_info)
        if "parameter_ranges/clear_mode" in full_info:
            self.base.w[self.gui_name].set_options(full_info["parameter_ranges/clear_mode"],index=0)
        else:
            self.disable()

class ClearCyclesParameter(cam_gui_parameters.IntGUIParameter):
    """
    PVCam clear cycles parameter.
    
    Gets disabled if not supported by the camera.
    """
    def __init__(self, settings):
        super().__init__(settings,"clear_cycles","Clear cycles",limit=(0,None))
    def setup(self, parameters, full_info):
        super().setup(parameters,full_info)
        if "camera_attributes/CLEAR_CYCLES" not in full_info:
            self.disable()

class ReadoutModeParameter(cam_gui_parameters.EnumGUIParameter):
    """
    PVCam readout mode parameter.
    
    Receives possible values from the camera.
    """
    def __init__(self, settings):
        super().__init__(settings,"readout_mode","Mode",{(0,0,0):"Default"})
        self.add_indicator="next_line"
    def add(self, base):
        with base.using_new_sublayout("readout_mode","grid"):
            return super().add(base)
    def setup(self, parameters, full_info):
        super().setup(parameters,full_info)
        if "readout_modes" in full_info:
            readout_modes=full_info["readout_modes"]
            options=["{}, {:.0f}MHz, {}".format(m.port_name,m.speed_freq/1E6,m.gain_name) for m in readout_modes]
            index_values=[(m.port_idx,m.speed_idx,m.gain_idx) for m in readout_modes]
            self.base.w[self.gui_name].set_options(options,index_values=index_values,value=index_values[0])
        else:
            self.disable()


class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="indicator"
    def get_basic_parameters(self, name):
        if name=="trigger_mode": return TriggerModeParameter(self)
        return super().get_basic_parameters(name)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(ReadoutModeParameter(self),"advanced")
        self.add_parameter(ClearModeParameter(self),"advanced")
        self.add_parameter(ClearCyclesParameter(self),"advanced")




class PvcamCameraDescriptor(ICameraDescriptor):
    _cam_kind="pvcam"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Pvcam cameras")
        try:
            cams=Photometrics.list_cameras()
        except (Photometrics.PvcamError, OSError):
            if verbose: print("Error loading or running the Pvcam library: required software (Photometrics PVCAM) must be missing\n")
            return
        cam_num=len(cams)
        if not cam_num:
            if verbose: print("Found no Pvcam cameras\n")
            return
        if verbose: print("Found {} Pvcam camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for name in cams:
            try:
                with Photometrics.PvcamCamera(name) as cam:
                    device_info=cam.get_device_info()
                    if verbose: print("Found Pvcam camera name={}, product {}, serial {}".format(name,device_info.product,device_info.serial))
                    yield cam,name
            except Photometrics.PvcamError:
                if verbose: print("Could not open Pvcam camera name={}".format(name))
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        device_info=cam.get_device_info()
        cam_desc=cls.build_cam_desc(params={"cam_name":info})
        cam_desc["display_name"]=" ".join(s for s in [device_info.vendor,device_info.system,device_info.serial] if s)
        cam_name="pvcam_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Photometrics PVCAM"
    
    def make_thread(self, name):
        return PvcamCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)