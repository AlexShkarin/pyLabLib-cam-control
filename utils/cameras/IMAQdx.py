from pylablib.devices import IMAQdx
from pylablib.thread.devices.IMAQdx import EthernetIMAQdxCameraThread

from .base import ICameraDescriptor
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI




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






class IMAQdxCameraDescriptor(ICameraDescriptor):
    _cam_kind="IMAQdx"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for IMAQdx cameras")
        try:
            cams=IMAQdx.list_cameras()
        except (IMAQdx.IMAQdxError, OSError, AttributeError):
            if verbose: print("Error loading or running the IMAQdx library: required software (NI IMAQdx) must be missing\n")
            return
        if len(cams)==0:
            if verbose: print("Found no IMAQdx cameras\n")
            return
        cam_num=len(cams)
        if verbose: print("Found {} IMAQdx camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i,cdesc in enumerate(cams):
            if verbose: print("Checking IMAQdx camera idx={}\n\tVendor {},   model {}".format(i,cdesc.vendor,cdesc.model))
            yield None,cdesc
    @classmethod
    def _generate_default_description(cls, idx, cam=None, info=None):
        cam_desc=cls.build_cam_desc(params={"name":info.name})
        cam_desc["display_name"]="{} {}".format(info.vendor,info.model)
        cam_name="imaqdx_{}".format(idx)
        return cam_name,cam_desc

    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        return None,None
    
    def make_gui_control(self, parent):
        return GenericCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)



class EthernetPhotonFocusIMAQdxCameraDescriptor(IMAQdxCameraDescriptor):
    _cam_kind="PhotonFocusLAN"
    _expands="IMAQdx"
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        if info.vendor.lower().startswith("photonfocus") and info.model.lower().startswith("hd1"):
            return super()._generate_default_description(idx,cam=cam,info=info)
    def get_kind_name(self):
        return "PhotonFocus Ethernet"
    def make_thread(self, name):
        return EthernetPhotonFocusIMAQdxCameraThread(name=name,kwargs=self.settings["params"].as_dict())