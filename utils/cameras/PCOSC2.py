from pylablib.devices import PCO
from pylablib.thread.devices.PCO import PCOSC2CameraThread

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI






class BasicPCOSC2CameraThread(PCOSC2CameraThread):
    def setup_open_device(self):
        super().setup_open_device()
        self.device.set_status_line_mode(True,False)
        self._status_line_enabled=True
        try:
            self.device.enable_pixel_correction()
        except self.device.Error:
            pass



class FastScanBoolGUIParameter(cam_gui_parameters.BoolGUIParameter):
    """Fast scan parameter"""
    def __init__(self, settings):
        super().__init__(settings,"fast_scan","Fast scan",default=True,cam_name="pixel_rate")
    def to_camera(self, gui_value):
        return None if gui_value else 0
    def display(self, parameters):
        if "pixel_rate" in parameters and "all_pixel_rates" in parameters:
            self.settings.i[self.gui_name]=(parameters["pixel_rate"]==parameters["all_pixel_rates"][-1])

class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(FastScanBoolGUIParameter(self),"advanced")

class Status_GUI(GenericCameraStatus_GUI):
    def setup_status_table(self):
        self.add_text_label("buffer_overruns:",label="Buffer overruns")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "internal_buffer_status" in params:
            buffer_overruns=params["internal_buffer_status"].overruns
            self.v["buffer_overruns"]=str(buffer_overruns) if buffer_overruns is not None else "N/A"
            self.w["buffer_overruns"].setStyleSheet("font-weight: bold" if buffer_overruns else "")



class PCOCameraDescriptor(ICameraDescriptor):
    _cam_kind="PCOSC2"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for PCO cameras")
        try:
            cam_num=PCO.get_cameras_number()
        except (PCO.PCOSC2Error, OSError):
            if verbose: print("Error loading or running the PCO SC2 library: required software (PCO SDK) must be missing\n")
            return
        if cam_num==0:
            if verbose: print("Found no PCO cameras\n")
            return
        if verbose: print("Found {} PCO camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i in range(cam_num):
            try:
                if verbose: print("Found PCO camera idx={}".format(i))
                with PCO.PCOSC2Camera(idx=i) as cam:
                    device_info=cam.get_device_info()
                    if verbose: print("\tModel {}, serial number {}".format(device_info.model,device_info.serial_number))
                    yield cam,None
            except PCO.PCOSC2Error:
                pass
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        device_info=cam.get_device_info()
        cam_desc=cls.build_cam_desc(params={"idx":idx})
        cam_desc["display_name"]="{} {}".format(device_info.model,device_info.serial_number)
        cam_name="pcosc2_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Generic PCO"
    
    def make_thread(self, name):
        return BasicPCOSC2CameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return Status_GUI(parent,cam_desc=self)