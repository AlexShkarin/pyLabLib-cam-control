from pylablib.devices import PhotonFocus, IMAQ, SiliconSoftware
from pylablib.thread.devices.PhotonFocus import IMAQPhotonFocusCameraThread as BaseIMAQPhotonFocusCameraThread, SiliconSoftwarePhotonFocusCameraThread
from pylablib.core.thread import controller

from .base import ICameraDescriptor
from ..gui import cam_gui_parameters, cam_attributes_browser
from ..gui.base_cam_ctl_gui import GenericCameraSettings_GUI, GenericCameraStatus_GUI









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
        super()._update_additional_parameters(parameters)
    def _read_send_images(self):
        nsent=super()._read_send_images()
        for name,par in self.trigger_monitors.items():
            curr_state,cnt=self.v["trigger_monitors",name]
            new_state=self.device.read_trigger(*par)
            if not curr_state and new_state:
                cnt+=1
            self.v["trigger_monitors",name]=new_state,cnt
        return nsent





class CamAttributesBrowser(cam_attributes_browser.CamAttributesBrowser):
    def _add_attribute(self, name, attribute, value):
        if not attribute.readable:
            return
        indicator=not attribute.writable
        if attribute.kind in {"INT","UINT"}:
            self._record_attribute(name,"int",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_integer_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="FLOAT":
            self._record_attribute(name,"float",attribute,indicator=indicator,rng=(attribute.min,attribute.max))
            self.add_float_parameter(name,attribute.name,limits=(attribute.min,attribute.max),indicator=indicator)
        elif attribute.kind=="MODE":
            if attribute.values:
                self._record_attribute(name,"enum",attribute,indicator=indicator,rng=attribute.ilabels)
                self.add_choice_parameter(name,attribute.name,attribute.ilabels,indicator=indicator)
        elif attribute.kind=="STRING":
            self._record_attribute(name,"str",attribute,indicator=indicator)
            self.add_string_parameter(name,attribute.name,indicator=indicator)
        elif attribute.kind=="BOOL":
            self._record_attribute(name,"bool",attribute,indicator=indicator)
            self.add_bool_parameter(name,attribute.name,indicator=indicator)
    def _get_attribute_range(self, attribute):
        if attribute.kind in ["int","float"]:
            return (attribute.min,attribute.max)
        if attribute.kind=="enum":
            return attribute.ilabels


class BlackOffsetParameter(cam_gui_parameters.IGUIParameter):
    def add(self, base):
        self.base=base
        self.base.add_check_box("change_bl_offset","Change black level offset",False,add_indicator=False)
        self.base.add_num_edit("bl_offset",value=3072,limiter=(0,None,"coerce","int"),formatter="int",label="Black level offset")
        self.base.vs["change_bl_offset"].connect(controller.exsafe(lambda v: self.base.set_enabled("bl_offset",v)))
        self.base.set_enabled("bl_offset",False)
        self.connect_updater(["bl_offset","change_bl_offset"])
    def _update_value(self, v):
        if self.base.v["change_bl_offset"]:
            super()._update_value(v)
    def collect(self, parameters):
        if self.base.v["change_bl_offset"]:
            parameters["bl_offset"]=self.base.v["bl_offset"]
        return super().collect(parameters)
    def display(self, parameters):
        if "bl_offset" in parameters:
            self.base.i["bl_offset"]=parameters["bl_offset"]
        return super().display(parameters)
class ROIGUIParameter(cam_gui_parameters.ROIGUIParameter):
    def _is_diff_update_allowed(self, oldv, newv):
        return oldv and all([(cr.max-cr.min==pr.max-pr.min) and (cr.bin==pr.bin) for (cr,pr) in zip(oldv,newv)])


class PhotonFocusCameraSettings_GUI(GenericCameraSettings_GUI):
    _roi_kind="minsize"
    _param_dependencies={"cfr":["trigger_interleave","frame_period"],"trigger_interleave":["cfr","frame_period"]}
    def get_basic_parameters(self, name):
        """Get basic GUI parameters, which can be shared between different cameras"""
        if name=="exposure": return cam_gui_parameters.FloatGUIParameter(self,"exposure","Exposure (ms)",limit=(0,None),fmt=".4f",default=100,factor=1E3)
        if name=="frame_period": return cam_gui_parameters.FloatGUIParameter(self,"frame_period","Frame period (ms)",limit=(0,None),fmt=".4f",default=0,factor=1E3)
        if name=="roi": return ROIGUIParameter(self,bin_kind=self._bin_kind,roi_kind=self._roi_kind)
        if name=="cfr": return cam_gui_parameters.BoolGUIParameter(self,"cfr","Constant frame rate",default=True)
        if name=="bl_offset": return BlackOffsetParameter(self)
        if name=="status_line": return cam_gui_parameters.BoolGUIParameter(self,"status_line","Status line",default=True)
        if name=="perform_status_check": return cam_gui_parameters.BoolGUIParameter(self,"perform_status_check","Perform status line check",default=True,add_indicator=False,indirect=True)
        if name=="trigger_interleave": return cam_gui_parameters.BoolGUIParameter(self,"trigger_interleave","Simultaneous readout (interleave)",default=True)
        return super().get_basic_parameters(name)
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.common_params.insert_row(2)
        self.add_builtin_parameter("cfr","common",row=2)
        self.add_builtin_parameter("bl_offset","advanced")
        self.add_builtin_parameter("trigger_interleave","advanced")
        self.add_builtin_parameter("status_line","advanced").allow_diff_update=True
        self.add_builtin_parameter("perform_status_check","advanced").allow_diff_update=True
        self.advanced_params.vs["status_line"].connect(controller.exsafe(lambda v: self.advanced_params.set_enabled("perform_status_check",v)))
        self.add_parameter(cam_gui_parameters.AttributesBrowserGUIParameter(self,CamAttributesBrowser),"advanced")
    def collect_parameters(self):
        parameters=super().collect_parameters()
        parameters["perform_status_check"]&=parameters["status_line"]
        return parameters
    def show_parameters(self, parameters):
        super().show_parameters(parameters)
        self.common_params.set_enabled("frame_period",parameters.get("cfr",False))

class PhotonFocusIMAQCameraSettings_GUI(PhotonFocusCameraSettings_GUI):
    """Settings table widget for Photon Focus IMAQ camera"""
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.add_parameter(cam_gui_parameters.BoolGUIParameter(self,"output_vsync","Output VSync trigger",indirect=True),"advanced",row=1)
    def collect_parameters(self):
        parameters=super().collect_parameters()
        if parameters["trigger_mode"]=="ext":
            parameters["trigger_mode"]="in_ext"
        elif parameters["output_vsync"]:
            parameters["trigger_mode"]="out"
        else:
            parameters["trigger_mode"]="int"
        del parameters["output_vsync"]
        return parameters
    def show_parameters(self, parameters):
        super().show_parameters(parameters)
        if "trigger_mode" in parameters:
            self.i["output_vsync"]=parameters["trigger_mode"]=="out"
            self.i["trigger_mode"]="ext" if parameters["trigger_mode"]=="in_ext" else "int"
class PhotonFocusSiliconSoftwareCameraSettings_GUI(PhotonFocusCameraSettings_GUI):
    """Settings table widget for Photon Focus SiliconSoftware camera"""





class PhotonFocusCameraStatus_GUI(GenericCameraStatus_GUI):
    def setup_status_table(self):
        self.add_num_label("frames_lost",formatter=("int"),label="Frames lost:")
    def show_parameters(self, params):
        super().show_parameters(params)
        if "buffer_status" in params:
            bstat=params["buffer_status"]
            self.v["frames/buffstat"]="{:d} / {:d}".format(bstat.unread or 0,bstat.size or 0)
            self.v["frames_lost"]=bstat.lost
            self.w["frames_lost"].setStyleSheet("font-weight: bold" if bstat.lost else "")





class PhotonFocusCameraDescriptor(ICameraDescriptor):
    _cam_kind="PhotonFocus"

    @classmethod
    def iterate_cameras(cls, verbose=False):
        if verbose: print("Searching for PhotonFocus cameras (might take several minutes)")
        try:
            pf_cams=PhotonFocus.list_cameras(only_supported=False)
        except (PhotonFocus.PFCamError, OSError):
            if verbose: print("Error loading or running the PFCam library: required software (PhotonFocus PFRemote) must be missing\n")
            if verbose=="full": cls.print_error()
            return
        pf_cams=[(p,d) for (p,d) in pf_cams if d.manufacturer!="RS-232"]  # these usually don't have cameras, but can lead to very long polling times
        if len(pf_cams)==0:
            if verbose: print("Found no PhotonFocus cameras\n")
            return
        if verbose: print("Checking potential PFRemote interfaces {}\n".format(", ".join(["{}/{}".format(d.manufacturer,d.port) for _,d in pf_cams])))
        cams=[]
        for p,cdesc in pf_cams:
            if verbose: print("Checking interface {}/{} ... ".format(cdesc.manufacturer,cdesc.port),end="")
            name=PhotonFocus.query_camera_name(p)
            if name is not None:
                if verbose: print("discovered camera {}".format(name))
                cams.append((p,cdesc))
            else:
                if verbose: print("not a camera")
        cam_num=len(cams)
        if verbose: print("Found {} PhotonFocus camera{}".format(cam_num,"s" if cam_num>1 else ""))
        for p,cdesc in cams:
            if verbose: print("Checking PhotonFocus camera idx={}\n\tPort {},   vendor {},   model {}".format(p,cdesc.port,cdesc.manufacturer,name))
            yield None,(p,cdesc)
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        return None,None




class PhotonFocusIMAQCameraDescriptor(PhotonFocusCameraDescriptor):
    _cam_kind="PhotonFocusIMAQ"
    _expands="PhotonFocus"
    _imaq_interfaces=None
    @classmethod
    def _detect_interfaces(cls, verbose=False):
        if cls._imaq_interfaces is None:
            try:
                cls._imaq_interfaces=IMAQ.list_cameras()
            except (IMAQ.IMAQError, OSError):
                cls._imaq_interfaces=[]
                if verbose: print("Error loading or running the IMAQ library: required software (NI IMAQ) must be missing\n")
        return cls._imaq_interfaces
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        imaq_interfaces=cls._detect_interfaces(verbose=False)
        port,cdesc=info
        pfcam_port=(cdesc.manufacturer,cdesc.port)
        name=PhotonFocus.query_camera_name(port)
        cam_desc=cls.build_cam_desc({"pfcam_port":pfcam_port})
        cam_desc["display_name"]="{} port {}".format(name,port)
        for i,fg in enumerate(imaq_interfaces):
            try:
                cam=PhotonFocus.PhotonFocusIMAQCamera(imaq_name=fg,pfcam_port=pfcam_port)
            except PhotonFocus.PhotonFocusIMAQCamera.Error:
                continue
            try:
                if PhotonFocus.check_grabber_association(cam):
                    cam_name="ppimaq_{}".format(port)
                    cam_desc["params/imaq_name"]=imaq_interfaces.pop(i)
                    return cam_name,cam_desc
            except PhotonFocus.PhotonFocusIMAQCamera.Error:
                pass
            finally:
                cam.close()
    def get_kind_name(self):
        return "PhotonFocus + IMAQ"
    def make_thread(self, name):
        return IMAQPhotonFocusCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return PhotonFocusIMAQCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return PhotonFocusCameraStatus_GUI(parent,cam_desc=self)




class PhotonFocusSiSoCameraDescriptor(PhotonFocusCameraDescriptor):
    _cam_kind="PhotonFocusSiSo"
    _expands="PhotonFocus"
    _siso_boards=None
    @classmethod
    def _detect_interfaces(cls, verbose=False):
        if cls._siso_boards is None:
            try:
                cls._siso_boards=SiliconSoftware.list_boards()
            except (SiliconSoftware.SiliconSoftwareError, OSError):
                cls._siso_boards=[]
                if verbose: print("Error loading or running the Silicon Software library: required software (Silicon Software Runtime Environment) must be missing\n")
        return cls._siso_boards
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        siso_boards=cls._detect_interfaces(verbose=False)
        port,cdesc=info
        pfcam_port=(cdesc.manufacturer,cdesc.port)
        name=PhotonFocus.query_camera_name(port)
        cam_desc=cls.build_cam_desc({"pfcam_port":pfcam_port})
        cam_desc["display_name"]="{} port {}".format(name,port)
        for i in range(len(siso_boards)):
            applets=SiliconSoftware.list_applets(i)
            app=None
            if any(a.name=="DualAreaGray16" for a in applets):
                app="DualAreaGray16"
                ports=[0,1]
            elif any(a.name=="SingleAreaGray16" for a in applets):
                app="SingleAreaGray16"
                ports=[0]
            else:
                continue
            for p in ports:
                try:
                    cam=PhotonFocus.PhotonFocusSiSoCamera(siso_board=i,siso_applet=app,siso_port=p,pfcam_port=pfcam_port)
                except PhotonFocus.PhotonFocusSiSoCamera.Error:
                    continue
                try:
                    if PhotonFocus.check_grabber_association(cam):
                        cam_name="ppsiso_{}".format(p)
                        cam_desc["params/siso_board"]=i
                        cam_desc["params/siso_applet"]=app
                        cam_desc["params/siso_port"]=p
                        return cam_name,cam_desc
                except PhotonFocus.PhotonFocusSiSoCamera.Error:
                    pass
                finally:
                    cam.close()
    def get_kind_name(self):
        return "PhotonFocus + Silicon Software"
    def make_thread(self, name):
        return SiliconSoftwarePhotonFocusCameraThread(name=name,kwargs=self.settings["params"].as_dict())
    def make_gui_control(self, parent):
        return PhotonFocusSiliconSoftwareCameraSettings_GUI(parent,cam_desc=self)
    def make_gui_status(self, parent):
        return PhotonFocusCameraStatus_GUI(parent,cam_desc=self)