from pylablib.thread.devices.Andor import AndorSDK2CameraThread, AndorSDK3CameraThread, AndorSDK2IXONThread, AndorSDK2LucaThread, AndorSDK3ZylaThread
from pylablib.thread.devices.DCAM import DCAMCameraThread
from pylablib.thread.devices.uc480 import UC480CameraThread
from pylablib.thread.devices.PCO import PCOSC2CameraThread
from pylablib.thread.devices.PhotonFocus import IMAQPhotonFocusCameraThread as BaseIMAQPhotonFocusCameraThread, SiliconSoftwarePhotonFocusCameraThread
from pylablib.thread.devices.Thorlabs import ThorlabsTLCameraThread
from pylablib.thread.devices.IMAQdx import IMAQdxCameraThread, EthernetIMAQdxCameraThread
from pylablib.thread.devices.PrincetonInstruments import PicamCameraThread





class DCAMOrcaCameraThread(DCAMCameraThread):
    def _apply_additional_parameters(self, parameters):
        super()._apply_additional_parameters(parameters)
        self.device.set_defect_correct_mode(True)

class DCAMImagEMCameraThread(DCAMCameraThread):
    def _apply_additional_parameters(self, parameters):
        super()._apply_additional_parameters(parameters)
        if "sensitivity" in parameters:
            self.device.cav["SENSITIVITY"]=parameters["sensitivity"]
    def _update_additional_parameters(self, parameters):
        parameters["sensitivity"]=self.device.cav["SENSITIVITY"]
        return super()._update_additional_parameters(parameters)



class IMAQPhotonFocusCameraThread(BaseIMAQPhotonFocusCameraThread):
    """
    IMAQ-interfaced PhotonFocus camera device thread.

    See :class:`GenericCameraThread`.
    """
    def setup_task(self, imaq_name, pfcam_port, remote=None, misc=None):
        self.in_trigger_src=(misc or {}).get("trigger/in/src",("ext",0))
        self.out_trigger_dst=(misc or {}).get("trigger/out/dst",("ext",0))
        self.trigger_monitors={}
        super().setup_task(imaq_name,pfcam_port,remote=remote,misc=misc)
        self.add_command("add_trigger_monitor")
        self.add_command("remove_trigger_monitor")
    
    def add_trigger_monitor(self, name, source, line, polarity="low"):
        """
        Add "manual" monitor of the camera line which counts number of times it switches from 0 to 1.

        `source`, `line` and `polarity` specify the trigger source (polarity specifies "default" trigger state).
        Note that the trigger state is read out only after every frame readout, i.e., about every ``min_poll_period`` or every frame (whichever is longer);
        therefore, short pulses can be missed.
        """
        if self.device:
            self.trigger_monitors[name]=(source,line,polarity)
            self.v["trigger_monitors",name]=(self.device.read_trigger(source,line,polarity),0) # state, counter
    def remove_trigger_monitor(self, name):
        """Remove "manual" trigger monitor"""
        if self.device:
            del self.trigger_monitors[name]
            if name in self.v["trigger_monitors"]:
                del self.v["trigger_monitors",name]
    def _get_trigger_mode(self):
        if self.device.dv["triggers_in_cfg"]:
            return "in_ext"
        elif dict(self.device.dv["triggers_out_cfg"]).get(self.out_trigger_dst)==("high","vsync"):
            return "out"
        else:
            return "int"
    def _apply_additional_parameters(self, parameters):
        super()._apply_additional_parameters(parameters)
        curr_trig_mode=self._get_trigger_mode()
        new_trig_mode=parameters.get("trigger_mode",curr_trig_mode)
        if (new_trig_mode!=curr_trig_mode) and ((new_trig_mode=="in_ext") or (curr_trig_mode=="in_ext")):
            self.clear_acquisition()
            self.device.clear_all_triggers()
            if new_trig_mode=="in_ext":
                self.device.configure_trigger_in(self.in_trigger_src[0],self.in_trigger_src[1],"high","buffer")
        if new_trig_mode=="out":
            self.device.configure_trigger_out(self.out_trigger_dst[0],self.out_trigger_dst[1],"high","vsync")
        else:
            self.device.configure_trigger_out(self.out_trigger_dst[0],self.out_trigger_dst[1],"high","disable")
    def _update_additional_parameters(self, parameters):
        parameters["trigger_mode"]=self._get_trigger_mode()
    def _read_send_images(self):
        nsent=super()._read_send_images()
        for name,par in self.trigger_monitors.items():
            curr_state,cnt=self.v["trigger_monitors",name]
            new_state=self.device.read_trigger(*par)
            if not curr_state and new_state:
                cnt+=1
            self.v["trigger_monitors",name]=new_state,cnt
        return nsent



class PCOCameraThread(PCOSC2CameraThread):
    def setup_open_device(self):
        super().setup_open_device()
        self.device.set_status_line_mode(True,False)
        self._status_line_enabled=True
        try:
            self.device.enable_pixel_correction()
        except self.device.Error:
            pass


class EthernetPhotonFocusIMAQdxCameraThread(EthernetIMAQdxCameraThread):
    parameter_variables=EthernetIMAQdxCameraThread.parameter_variables|{"exposure"}
    def _apply_additional_parameters(self, parameters):
        super()._apply_additional_parameters(parameters)
        if "exposure" in parameters:
            self.device.cav["CameraAttributes/AcquisitionControl/ExposureTime"]=parameters["exposure"]*1E6
    def _update_additional_parameters(self, parameters):
        parameters["exposure"]=self.device.cav["CameraAttributes/AcquisitionControl/ExposureTime"]/1E6
        return super()._update_additional_parameters(parameters)
    def _estimate_buffers_num(self):
        if self.device:
            nframes=self.min_buffer_size[1]
            if "CameraAttributes/AcquisitionControl/AcquisitionFrameRateMax" in self.device.cav:
                n_rate=self.min_buffer_size[0]*self.device.cav["CameraAttributes/AcquisitionControl/AcquisitionFrameRateMax"]
                nframes=max(nframes,n_rate)
            return int(nframes)
        return None