from pylablib.devices import PrincetonInstruments
from pylablib.thread.devices.PrincetonInstruments import PicamCameraThread

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI





class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def _add_attribute(self, name, attribute, value):
        indicator=not attribute.writable
        if attribute.kind in {"Integer","Large Integer"}:
            self._record_attribute(name,"int",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_integer_parameter(name,attribute.name,limits=(attribute.min,attribute.max),default=attribute.default,indicator=indicator)
        elif attribute.kind=="Floating Point":
            self._record_attribute(name,"float",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_float_parameter(name,attribute.name,limits=(attribute.min,attribute.max),default=attribute.default,indicator=indicator)
        elif attribute.kind=="Enumeration":
            self._record_attribute(name,"enum",attribute,indicator=indicator,rng=attribute.ilabels)
            self.add_choice_parameter(name,attribute.name,attribute.ilabels,default=attribute.default,indicator=indicator)
        elif attribute.kind=="Boolean":
            self._record_attribute(name,"bool",attribute,indicator=indicator)
            self.add_bool_parameter(name,attribute.name,default=attribute.default,indicator=indicator)
    def _get_attribute_range(self, attribute):
        if attribute.kind in ["Integer","Large Integer","Floating Point"]:
            return (attribute.min,attribute.max)
        if attribute.kind=="Enumeration":
            return attribute.ilabels

class Settings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="indicator"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")




class PicamCameraDescriptor(ICameraDescriptor):
    _cam_kind="Picam"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Picam cameras")
        try:
            cams=PrincetonInstruments.list_cameras()
        except (PrincetonInstruments.PicamError, OSError):
            if verbose: print("Error loading or running the Picam library: required software (Princeton Instruments PICam) must be missing\n")
            if verbose=="full": cls.print_error()
            return
        if len(cams)==0:
            if verbose: print("Found no Picam cameras\n")
            return
        cam_num=len(cams)
        if verbose: print("Found {} Picam camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i,cdesc in enumerate(cams):
            if verbose: print("Found Picam camera serial number={}\n\tModel {},   name {}".format(i,cdesc.model,cdesc.name))
            yield None,cdesc
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        cam_desc=cls.build_cam_desc(params={"serial_number":info.serial_number})
        cam_desc["display_name"]="{} {}".format(info.model,info.serial_number)
        cam_name="picam_{}".format(idx)
        return cam_name,cam_desc
    
    def get_kind_name(self):
        return "Princeton Instruments PICam"
    
    def make_thread(self, name):
        return PicamCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)