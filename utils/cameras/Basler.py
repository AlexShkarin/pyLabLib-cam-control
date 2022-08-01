from pylablib.devices import Basler
from pylablib.thread.devices.Basler import BaslerPylonCameraThread
from pylablib.core.thread import controller

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI



class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def setup(self, cam_ctl):
        super().setup(cam_ctl)
        with self.buttons.using_layout("buttons"):
            self.buttons.add_combo_box("visibility",label="Visibility",options={"simple":"Simple","intermediate":"Intermediate","advanced":"Advanced","invisible":"Full"},value="simple",location=(0,0))
            self.buttons.vs["visibility"].connect(self.setup_visibility)
    def _add_attribute(self, name, attribute, value):
        if not attribute.readable:
            return
        indicator=not attribute.writable
        if attribute.kind=="int":
            self._record_attribute(name,"int",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_integer_parameter(name,attribute.display_name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="float":
            self._record_attribute(name,"float",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_float_parameter(name,attribute.display_name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="enum":
            self._record_attribute(name,"enum",attribute,indicator=indicator,rng=attribute.ilabels)
            self.add_choice_parameter(name,attribute.display_name,attribute.ilabels,indicator=indicator)
        elif attribute.kind=="str":
            self._record_attribute(name,"str",attribute,indicator=indicator)
            self.add_string_parameter(name,attribute.display_name,indicator=indicator)
        elif attribute.kind=="bool":
            self._record_attribute(name,"bool",attribute,indicator=indicator)
            self.add_bool_parameter(name,attribute.display_name,indicator=indicator)
    def _get_attribute_range(self, attribute):
        if attribute.kind in ["int","float"]:
            return (attribute.min,attribute.max)
        if attribute.kind=="enum":
            return attribute.ilabels
    @controller.exsafe
    def setup_visibility(self):
        quick=self.buttons.v["quick_access"]
        vis=self.buttons.v["visibility"]
        vis_order=["simple","intermediate","advanced","invisible","unknown"]
        for n in self._attributes:
            vis_pass=vis_order.index(self._attributes[n].attribute.visibility)<=vis_order.index(vis)
            self._show_attribute(n,(not quick or self.props_table.v["p_quick",n]) and vis_pass)
    def setup_parameters(self, full_info):
        super().setup_parameters(full_info)
        self.setup_visibility()



class Settings_GUI(GenericCameraSettings_GUI):
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")



class BaslerPylonCameraDescriptor(ICameraDescriptor):
    _cam_kind="BaslerPylon"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for Basler cameras")
        try:
            cams=Basler.list_cameras()
        except (Basler.BaslerError, OSError, AttributeError):
            if verbose: print("Error loading or running the Basler library: required software (Basler pylon) must be missing\n")
            if verbose=="full": cls.print_error()
            return
        if len(cams)==0:
            if verbose: print("Found no Basler cameras\n")
            return
        cam_num=len(cams)
        if verbose: print("Found {} Basler camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for i,cdesc in enumerate(cams):
            if verbose: print("Checking Basler camera idx={}\n\tVendor {},   model {}".format(i,cdesc.vendor,cdesc.model))
            yield None,cdesc
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        cam_desc=cls.build_cam_desc(params={"name":info.name})
        cam_desc["display_name"]="{} {}".format(info.vendor,info.model)
        cam_name="basler_pylon_{}".format(idx)
        return cam_name,cam_desc

    def get_kind_name(self):
        return "Generic Basler pylon"
    def make_thread(self, name):
        return BaslerPylonCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    
    def make_gui_control(self, parent):
        return Settings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return GenericCameraStatus_GUI(parent,cam_desc=self)