from pylablib.devices import IMAQdx
from pylablib.thread.devices.IMAQdx import IMAQdxCameraThread, EthernetIMAQdxCameraThread
from pylablib.core.thread import controller

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
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


class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def setup(self, cam_ctl):
        super().setup(cam_ctl)
        with self.buttons.using_layout("buttons"):
            self.buttons.add_combo_box("visibility",label="Visibility",options={"simple":"Simple","intermediate":"Intermediate","advanced":"Advanced"},value="simple",location=(0,0))
            self.buttons.vs["visibility"].connect(self.setup_visibility)
    def _add_attribute(self, name, attribute, value):
        if not attribute.readable:
            return
        indicator=not attribute.writable
        if attribute.kind in ["u32","i64"]:
            self._record_attribute(name,"int",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_integer_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="f64":
            self._record_attribute(name,"float",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_float_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="enum":
            self._record_attribute(name,"enum",attribute,indicator=indicator,rng=attribute.ilabels)
            self.add_choice_parameter(name,attribute.name,attribute.ilabels,indicator=indicator)
        elif attribute.kind=="str":
            self._record_attribute(name,"str",attribute,indicator=indicator)
            self.add_string_parameter(name,attribute.name,indicator=indicator)
        elif attribute.kind=="bool":
            self._record_attribute(name,"bool",attribute,indicator=indicator)
            self.add_bool_parameter(name,attribute.name,indicator=indicator)
    def _get_attribute_range(self, attribute):
        if attribute.kind in ["u32","i64","f64"]:
            return (attribute.min,attribute.max)
        if attribute.kind=="enum":
            return attribute.ilabels
    @controller.exsafe
    def setup_visibility(self):
        quick=self.buttons.v["quick_access"]
        vis=self.buttons.v["visibility"]
        vis_order=["simple","intermediate","advanced"]
        for n in self._attributes:
            vis_pass=vis_order.index(self._attributes[n].attribute.visibility)<=vis_order.index(vis)
            self._show_attribute(n,(not quick or self.props_table.v["p_quick",n]) and vis_pass)
    def setup_parameters(self, full_info):
        super().setup_parameters(full_info)
        self.setup_visibility()



class Settings_GUI(GenericCameraSettings_GUI):
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")



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
    def get_kind_name(self):
        return "Generic IMAQdx"
    def make_thread(self, name):
        return IMAQdxCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
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