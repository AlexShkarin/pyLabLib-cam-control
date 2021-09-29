from pylablib.core.utils import general
from pylablib.core.thread import controller
from pylablib.core.gui.widgets import container, param_table
from pylablib.gui.widgets import range_controls


##### Parameter tables tables #####

class ICameraSettings_GUI(container.QWidgetContainer):
    """
    Generic camera settings table widget.

    Sets up basic functions (connect/disconnect, start/stop streaming, applying settings).
    Other settings tables inherit from this one.

    Methods to overload:
        setup_settings_tables: setup settings table entries; called on setup to add settings widgets
        setup_gui_parameters: setup sub-widgets appearance (mostly enabling/disabling widgets); called every time before :meth:`show_parameters` is called
        collect_parameters: get camera parameters from the GUI as a dictionary
        show_parameters: set camera parameter indicators in the GUI
    """
    _param_dependencies={} # dictionary ``{name: [deps]}`` with parameter dependencies: when parameter ``name`` is updated, all dependent parameters should be updated as well (only applies to diff parameter update)
    _param_no_autoapply={"roi_indicator","size_indicator","show_gui_roi","show_det_size"} # parameters whose change does not call autoapply
    _param_only_diff={"add_info"} # parameters whose change produces diff update (i.e., full parameter update is not required)
    def setup(self, ctl):
        super().setup(no_margins=True)
        self.cam_ctl=ctl

        self._roi_kind=self.cam_ctl.settings.get("interface/cam_control/roi_kind",self._roi_kind)
        self._prev_params={}
        settings_tabs=container.QTabContainer(self)
        self.add_child("settings_tabs",settings_tabs)
        settings_tabs.setup()
        self.common_params=param_table.ParamTable(self)
        settings_tabs.add_tab("common","Common").add_child("common_params",self.common_params)
        self.common_params.setup(add_indicator=True)
        self.advanced_params=param_table.ParamTable(self)
        settings_tabs.add_tab("advanced","Advanced").add_child("advanced_params",self.advanced_params)
        self.advanced_params.setup(add_indicator=True)
        # Setup camera settings table
        self.setup_settings_tables()
        self.common_params.add_padding()
        self.advanced_params.add_padding()
        self.common_params.update_indicators()
        self.advanced_params.update_indicators()
        self.settings_params=param_table.ParamTable(self)
        self.add_child("settings_params",self.settings_params)
        self.settings_params.setup(add_indicator=False)
        self.settings_params.add_check_box("auto_apply",caption="Apply automatically",value=True)
        self.settings_params.add_button("apply","Apply")
        self.settings_params.add_button("start","Start acquisition",location=("next",0,1,1))
        self.settings_params.add_button("stop","Stop acquisition",location=(-1,1,1,1))
        self.settings_params.add_button("connect","Connect",location=("next",0,1,1))
        self.settings_params.add_button("disconnect","Disconnect",location=(-1,1,1,1))
        self.settings_params.vs["apply"].connect(self.cam_ctl.send_parameters)
        self.settings_params.vs["start"].connect(self.cam_ctl.acq_start)
        self.settings_params.vs["stop"].connect(self.cam_ctl.acq_stop)
        self.settings_params.vs["connect"].connect(self.cam_ctl.dev_connect)
        self.settings_params.vs["disconnect"].connect(self.cam_ctl.dev_disconnect)
        self.settings_params.layout().setColumnStretch(1,0)
        @controller.exsafe
        def on_settings_change(name, value):
            if self.v["auto_apply"] and name not in self._param_no_autoapply:
                if name in self._prev_params:
                    only_diff=self._is_only_diff(name,value,self._prev_params[name])
                else:
                    only_diff=False
                self.cam_ctl.send_parameters(only_diff=only_diff,dependencies=self._param_dependencies)
            self._prev_params[name]=value
        self.common_params.contained_value_changed.connect(on_settings_change)
        self.advanced_params.contained_value_changed.connect(on_settings_change)
        # Connect buttons
        self.setEnabled(False)
    def _is_only_diff(self, name, curr, prev):
        return name in self._param_only_diff

    _bin_kind="none" # defines ROI control binning mode; can be "none" (no binning controlled), "same" (same binning for both axes), or "both" (separate binning for each axis)
    _roi_kind="minmax" # defines ROI control kind: either "minmax" (control min and max coordinates of the ROI box) or "minsize" (control min coordinate and size of the ROI box)
    def _add_roi_ctl(self):
        """Add ROI control along with aux controls (Full ROI button and rectangle display checkboxes)"""
        roi_ctl=range_controls.BinROICtl(self)
        roi_ctl.setup(xlim=(0,None),kind=self._roi_kind)
        roi_ctl.params.set_enabled("x_bin",self._bin_kind!="none")
        roi_ctl.params.set_enabled("y_bin",self._bin_kind not in {"same","none"})
        roi_ctl.set_value(((0,1E5,1),(0,1E5,1)))
        self.common_params.add_custom_widget("roi",roi_ctl)
        @controller.exsafeSlot()
        def _full_roi():
            xp,yp=roi_ctl.get_value()
            roi_ctl.set_value(((roi_ctl.xlim[0],roi_ctl.xlim[1],xp[2]),(roi_ctl.ylim[0],roi_ctl.ylim[1],yp[2])))
        self.common_params.add_button("set_full_roi","Full ROI",add_indicator=False,location=("next",2,1,1)).get_value_changed_signal().connect(lambda v: _full_roi())
        with self.common_params.using_new_sublayout("show_rectangles","hbox",location=("next",0,1,"end")):
            self.common_params.add_check_box("show_gui_roi","Show selected ROI",add_indicator=False)
            self.common_params.add_check_box("show_det_size","Show full frame",add_indicator=False)
        self.common_params.add_spacer(5)
        with self.common_params.using_new_sublayout("roi_labels","grid",location=("next",0,1,"end")):
            self.common_params.add_text_label("roi_indicator",label="ROI")
            self.common_params.add_text_label("size_indicator",label="Image size")
            self.common_params.get_sublayout().setColumnStretch(1,1)
        for n in ["roi","show_gui_roi","show_det_size"]:
            self.common_params.vs[n].connect(lambda v: self._on_roi_changed())
        self.cam_roi=None
    @controller.exsafeSlot()
    def _on_roi_changed(self):
        """
        Set up display of new ROI and full frame rectangles.
        """
        if self.cam_roi is not None:
            roi_ctl=self.common_params.w["roi"]
            current_roi=roi_ctl.get_value()
            det_size=(roi_ctl.xlim[1],roi_ctl.ylim[1])
            if self.cam_ctl.preprocess_thread:
                preprocessor=controller.sync_controller(self.cam_ctl.preprocess_thread)
                prep_bin=preprocessor.v["params/spat/bin"] if preprocessor.v["enabled"] else (1,1)
            else:
                prep_bin=(1,1)
            def _rel_span(src, dst):
                return dst[0]-src[0],dst[1]-src[0]
            full_bin=self.cam_roi[0][2]*prep_bin[1],self.cam_roi[1][2]*prep_bin[0]
            if self._bin_kind=="same":
                full_bin=full_bin[0],full_bin[0]
            x_cam_span=self.cam_roi[0][0]/full_bin[0],self.cam_roi[0][1]/full_bin[0]
            y_cam_span=self.cam_roi[1][0]/full_bin[1],self.cam_roi[1][1]/full_bin[1]
            x_gui_span=current_roi[0][0]/full_bin[0],current_roi[0][1]/full_bin[0]
            y_gui_span=current_roi[1][0]/full_bin[1],current_roi[1][1]/full_bin[1]
            x_rel_span=_rel_span(x_cam_span,x_gui_span)
            y_rel_span=_rel_span(y_cam_span,y_gui_span)
            center=(y_rel_span[0]+y_rel_span[1])/2,(x_rel_span[0]+x_rel_span[1])/2
            size=y_rel_span[1]-y_rel_span[0],x_rel_span[1]-x_rel_span[0]
            self.cam_ctl.plot_control("rectangles/set",("new_roi",center,size))
            self.cam_ctl.plot_control("rectangles/"+("show" if self.v["show_gui_roi"] else "hide"),("new_roi",))
            x_det_span=(0,det_size[0]/full_bin[0])
            y_det_span=(0,det_size[1]/full_bin[1])
            x_rel_span=_rel_span(x_cam_span,x_det_span)
            y_rel_span=_rel_span(y_cam_span,y_det_span)
            center=(y_rel_span[0]+y_rel_span[1])/2,(x_rel_span[0]+x_rel_span[1])/2
            size=y_rel_span[1]-y_rel_span[0],x_rel_span[1]-x_rel_span[0]
            self.cam_ctl.plot_control("rectangles/set",("det_size",center,size))
            self.cam_ctl.plot_control("rectangles/"+("show" if self.v["show_det_size"] else "hide"),("det_size",))

    def setup_settings_tables(self):
        """Setup settings table entries"""
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        """Get camera parameters as a dictionary"""
        params={}
        if "roi" in self.v:
            xroi,yroi=self.v["roi"]
            roi_len={"both":6,"same":5,"none":4}[self._bin_kind]
            params["roi"]=(xroi.min,xroi.max,yroi.min,yroi.max,xroi.bin,yroi.bin)[:roi_len]
        return params
    # Setup interface limits according to camera parameters
    def setup_gui_parameters(self, params):
        """Setup sub-widgets appearance"""
        self.setEnabled(True)
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        """Set camera parameter indicators"""
        self.setup_gui_parameters(params)
        if "roi" in params and "roi_indicator" in self.v:
            roi=params["roi"]
            roi_str="[{:d} - {:d}] x [{:d} - {:d}]".format(*roi)
            if self._bin_kind=="same":
                roi_str+="  Bin {:d}".format(roi[4])
            elif self._bin_kind=="both":
                roi_str+="  Bin {:d}x{:d}".format(*roi[4:6])
            self.v["roi_indicator"]=roi_str
            xbin=roi[4] if len(roi)>4 else 1
            ybin=roi[5] if len(roi)>5 else xbin
            size_str="{:d} x {:d}".format((roi[1]-roi[0])//xbin,(roi[3]-roi[2])//ybin)
            self.v["size_indicator"]=size_str
            self.cam_roi=(roi[0],roi[1],(roi[4] if len(roi)>4 else 1)),(roi[2],roi[3],(roi[5] if len(roi)>5 else 1))
            self._on_roi_changed()
    def _show_named_parameters(self, params, names):
        for n in names:
            if n in params:
                self.i[n]=params[n]






class GenericCameraSettings_GUI(ICameraSettings_GUI):
    """
    Settings table widget for a generic camera.

    Defines most common controls: exposue, ROI, trigger mode.
    Other settings tables inherit from this one.
    """
    _frame_period_kind="none"
    def setup_settings_tables(self):
        self.common_params.add_num_edit("exposure",100,limiter=(0,None,"coerce"),formatter=("float","auto",2,True),label="Exposure (ms)")
        if self._frame_period_kind=="value":
            self.common_params.add_num_edit("frame_period",0,limiter=(0,None,"coerce"),formatter=("float","auto",2,True),label="Frame period (ms)")
        elif self._frame_period_kind=="indicator":
            self.common_params.add_num_label("frame_period",0,limiter=(0,None,"coerce"),formatter=("float","auto",2,True),label="Frame period (ms)")
        self._add_roi_ctl()
        self.advanced_params.add_combo_box("trigger_mode","int",["Internal","External"],index_values=["int","ext"],label="Trigger mode")
        self.advanced_params.add_check_box("add_info",caption="Acquire frame info")
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["exposure"]=self.v["exposure"]*1E-3
        if self._frame_period_kind=="value":
            params["frame_period"]=self.v["frame_period"]*1E-3
        params["trigger_mode"]=self.v["trigger_mode"]
        params["add_info"]=self.v["add_info"]
        return params
    # Setup interface limits according to camera parameters
    def setup_gui_parameters(self, params):
        super().setup_gui_parameters(params)
        self.common_params.set_enabled("exposure","exposure" in params)
        self.advanced_params.set_enabled("trigger_mode","trigger_mode" in params)
        if "roi" not in params or "roi_limits" not in params:
            self.common_params.set_enabled(["roi","roi_indicator"],False)
        else:
            hlim,vlim=params["roi_limits"]
            maxbin=max(hlim.maxbin,vlim.maxbin)
            self.common_params.w["roi"].set_limits(xlim=(0,hlim.max),ylim=(0,vlim.max),minsize=(hlim.min,vlim.min),maxbin=maxbin)
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "exposure" in params:
            self.i["exposure"]=params["exposure"]/1E-3
        if "add_info" in params:
            self.i["add_info"]=params["add_info"]
        if "frame_period" in params:
            if self._frame_period_kind=="value":
                self.i["frame_period"]=params["frame_period"]/1E-3
            elif self._frame_period_kind=="indicator":
                self.v["frame_period"]=params["frame_period"]/1E-3
        if "trigger_mode" in params:
            try:
                self.i["trigger_mode"]=params["trigger_mode"]
            except ValueError:
                self.i["trigger_mode"]="int"




class IXONCameraSettings_GUI(GenericCameraSettings_GUI):
    """
    Settings table widget for Andor IXON camera.
    """
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.common_params.insert_row(0)
        self.common_params.add_combo_box("shutter","closed",["Opened","Closed","Auto"],index_values=["open","closed","auto"],label="Shutter",location=0)
        self.advanced_params.add_check_box("frame_transfer","Frame transfer mode",value=False)
        self.advanced_params.add_combo_box("hsspeed",0,["10 MHz","5 MHz","3 MHz","1 MHz"],label="Horizontal shift speed")
        self.advanced_params.add_combo_box("vsspeed",0,["0.3 us","0.5 us","0.9 us","1.7 us","3.3 us"],label="Vertical shift period")
        self.advanced_params.add_combo_box("preamp",0,["1","2.5","5.1"],label="Preamp gain")
        self.advanced_params.add_num_edit("EMCCD_gain",0,limiter=(0,255,"coerce","int"),formatter=("int"),label="EMCCD gain")
        self.advanced_params.add_combo_box("fan_mode","off",["Off","Low","Full"],index_values=["off","low","full"],label="Fan")
        self.advanced_params.add_combo_box("cooler",1,["Off","On"],label="Cooler")
        self.advanced_params.add_num_edit("temperature",-100,limiter=(-120,30,"coerce","int"),formatter="int",label="Temperature (C)")
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["EMCCD_gain"]=(self.v["EMCCD_gain"],False)
        for p in ["shutter","cooler","fan_mode","temperature","hsspeed","vsspeed","preamp","frame_transfer"]:
            params[p]=self.v[p]
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "shitter" in params:
            self.i["shutter"]=params["shutter"][0]
        if "EMCCD_gain" in params:
            self.i["EMCCD_gain"]=params["EMCCD_gain"][0]
        self._show_named_parameters(params,["cooler","fan_mode","temperature","hsspeed","vsspeed","preamp","frame_transfer"])


class LucaCameraSettings_GUI(GenericCameraSettings_GUI):
    """
    Settings table widget for Andor Luca camera.
    """
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.add_check_box("frame_transfer","Frame transfer mode",value=False)
        self.advanced_params.add_num_edit("EMCCD_gain",0,limiter=(0,255,"coerce","int"),formatter=("int"),label="EMCCD gain")
        self.advanced_params.add_combo_box("fan_mode","off",["Off","Full"],index_values=["off","full"],label="Fan")
        self.advanced_params.add_combo_box("cooler","off",["Off","On"],index_values=["off","on"],label="Cooler")
        self.advanced_params.add_num_edit("temperature",-20,limiter=(-40,30,"coerce","int"),formatter="int",label="Temperature (C)")
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["EMCCD_gain"]=(self.v["EMCCD_gain"],False)
        for p in ["cooler","fan_mode","temperature","frame_transfer"]:
            params[p]=self.v[p]
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "EMCCD_gain" in params:
            self.i["EMCCD_gain"]=params["EMCCD_gain"][0]
        self._show_named_parameters(params,["cooler","fan_mode","temperature","frame_transfer"])


class ZylaCameraSettings_GUI(GenericCameraSettings_GUI):
    """
    Settings table widget for Andor Zyla camera.
    """
    _bin_kind="both"
    _frame_period_kind="value"


class DCAMCameraSettings_GUI(GenericCameraSettings_GUI):
    """
    Settings table widget for Hamamatsu Orca Flash camera.
    """
    _bin_kind="same"
    _frame_period_kind="indicator"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.add_combo_box("readout_speed",label="Readout speed",options=["Slow","Normal","Fast"],index_values=["slow","normal","fast"])
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["readout_speed"]=self.v["readout_speed"]
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        self._show_named_parameters(params,["readout_speed"])


class DCAMImagEMCameraSettings_GUI(DCAMCameraSettings_GUI):
    """
    Settings table widget for Hamamatsu Orca Flash camera.
    """
    _bin_kind="same"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.add_num_edit("sensitivity",0,limiter=(0,255,"coerce","int"),formatter=("int"),label="EMCCD sensitivity")
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["sensitivity"]=self.v["sensitivity"]
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        self._show_named_parameters(params,["sensitivity"])
        

class PhotonFocusCameraSettings_GUI(GenericCameraSettings_GUI):
    """
    Settings table widget for a generic Photon Focus camera.
    """
    _roi_kind="minsize"
    _frame_period_kind="value"
    _param_dependencies={"cfr":["trigger_interleave","frame_period"],"trigger_interleave":["cfr","frame_period"]}
    _param_only_diff=GenericCameraSettings_GUI._param_only_diff|{"roi","status_line","perform_status_check"}
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.common_params.w["exposure"].set_formatter(("float","auto",4,True))
        self.common_params.w["frame_period"].set_formatter(("float","auto",4,True))
        self.common_params.insert_row(2)
        self.common_params.add_check_box("cfr","Constant frame rate",True,location=2)
        self.advanced_params.add_check_box("change_bl_offset","Change black level offset",False,add_indicator=False)
        self.advanced_params.add_num_edit("bl_offset",value=3072,limiter=(0,None,"coerce","int"),formatter="int",label="Black level offset")
        self.advanced_params.set_enabled("bl_offset",False)
        self.advanced_params.vs["change_bl_offset"].connect(lambda v: self.advanced_params.set_enabled("bl_offset",v))
        self.advanced_params.add_check_box("trigger_interleave","Simultaneous readout (interleave)",True)
        self.advanced_params.add_check_box("status_line","Status line",True)
        self.advanced_params.vs["status_line"].connect(lambda v: self.advanced_params.set_enabled("perform_status_check",v))
        self.advanced_params.add_check_box("perform_status_check","Perform status line check",True,add_indicator=False)
    def _is_only_diff(self, name, curr, prev):
        if name=="roi":
            return "roi" in self._param_only_diff and all([(cr.max-cr.min==pr.max-pr.min) and (cr.bin==pr.bin) for (cr,pr) in zip(curr,prev)])
        return super()._is_only_diff(name,curr,prev)
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        for p in ["trigger_interleave","status_line","cfr","perform_status_check"]:
            params[p]=self.v[p]
        if self.v["change_bl_offset"]:
            params["bl_offset"]=self.v["bl_offset"]
        return params
    # Setup interface limits according to camera parameters
    def setup_gui_parameters(self, params):
        super().setup_gui_parameters(params)
        frametime_enabled=params.get("cfr",False)
        self.common_params.set_enabled("frame_period",frametime_enabled)
    def show_parameters(self, params):
        super().show_parameters(params)
        self._show_named_parameters(params,["trigger_interleave","status_line","bl_offset"])
class PhotonFocusIMAQCameraSettings_GUI(PhotonFocusCameraSettings_GUI):
    """
    Settings table widget for Photon Focus IMAQ camera.
    """
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.insert_row(1)
        self.advanced_params.add_check_box("output_vsync","Output VSync trigger",False,location=1)
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        if self.v["trigger_mode"]=="ext":
            params["trigger_mode"]="in_ext"
        elif self.v["output_vsync"]:
            params["trigger_mode"]="out"
        else:
            params["trigger_mode"]="int"
        return params
    def show_parameters(self, params):
        super().show_parameters(params)
        if "trigger_mode" in params:
            self.i["output_vsync"]=params["trigger_mode"]=="out"
            self.i["trigger_mode"]="ext" if params["trigger_mode"]=="in_ext" else "int"
class PhotonFocusSiliconSoftwareCameraSettings_GUI(PhotonFocusCameraSettings_GUI):
    """
    Settings table widget for Photon Focus SiliconSoftware camera.
    """


class PCOGenericCameraSettings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.add_check_box("fast_scan","Fast scan",True)
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["pixel_rate"]=None if self.v["fast_scan"] else 0
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "pixel_rate" in params and "all_pixel_rates" in params:
            self.i["fast_scan"]=(params["pixel_rate"]==params["all_pixel_rates"][-1])


class UC480CameraSettings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"
    _frame_period_kind="value"
    def setup_settings_tables(self):
        super().setup_settings_tables()
        self.advanced_params.add_num_edit("pixel_rate",limiter=(0,None,"coerce"),formatter=("float","auto",1,True),label="Pixel rate (MHz)")
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        params=super().collect_parameters()
        params["pixel_rate"]=self.v["pixel_rate"]*1E6
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "pixel_rate" in params:
            self.i["pixel_rate"]=params["pixel_rate"]/1E6
        

class ThorlabsTLCameraSettings_GUI(GenericCameraSettings_GUI):
    _bin_kind="both"








##### Status tables #####

class GenericCameraStatus_GUI(param_table.StatusTable):
    """
    Generic camera status table.

    Defines most common status displays: frames status (acquired, read, etc.), buffer status, saving status.
    Other status tables inherit from this one.

    Methods to overload:
        setup_status_table: setup status table entries; called on setup to add status lines
        show_parameters: set camera status in the GUI
    """
    def setup(self, ctl):
        param_table.StatusTable.setup(self,"status_table")
        self.cam_ctl=ctl
        self.add_text_label("cam_name",label="Name:")
        self.w["cam_name"].setMaximumWidth(130)
        self.add_text_label("cam_kind",label="Kind:")
        # self.add_text_label("cam_model",label="Model:")
        self.add_status_line("connection",label="Connection:",srcs=self.cam_ctl.cam_thread,tags="status/connection_text")
        self.add_spacer(5)
        self.add_status_line("acquisition",label="Acquisition:",srcs=self.cam_ctl.cam_thread,tags="status/acquisition_text")
        self.add_num_label("frames/acquired",formatter=("int"),label="Frames acquired:")
        self.add_num_label("frames/read",formatter=("int"),label="Frames read:")
        self.add_text_label("frames/buffstat",label="Buffer fill status:")
        self.add_num_label("frames/fps",formatter=("float","auto",2),label="FPS:")
        self.setup_status_table()
        self.add_padding()
    def setup_status_table(self):
        """Setup status table entries"""
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        """Update camera status lines"""
        for p in ["frames/read","frames/acquired","frames/fps"]:
            if p in params:
                self.v[p]=params[p]
        if "frames/buffer_filled" in params and "buffer_size" in params:
            self.v["frames/buffstat"]="{:d} / {:d}".format(params["frames/buffer_filled"],params["buffer_size"])
        else:
            self.v["frames/buffstat"]="N/A"



class IXONCameraStatus_GUI(GenericCameraStatus_GUI):
    """
    Status table widget for Andor IXON camera.
    """
    def setup_status_table(self):
        self.add_text_label("temperature_status",label="Temperature status:")
        self.add_num_label("temperature_monitor",formatter=("float","auto",1,True),label="Temperature (C):")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "temperature_monitor" in params:
            self.v["temperature_monitor"]=params["temperature_monitor"]
        temp_status_text={"off":"Cooler off","not_reached":"Approaching...","not_stabilized":"Stabilizing...","drifted":"Drifted","stabilized":"Stable"}
        if "temperature_status" in params:
            self.v["temperature_status"]=temp_status_text[params["temperature_status"]]

LucaCameraStatus_GUI=IXONCameraStatus_GUI



class ZylaCameraStatus_GUI(GenericCameraStatus_GUI):
    """
    Status table widget for Andor Zyla camera.
    """
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



class PhotonFocusIMAQCameraStatus_GUI(GenericCameraStatus_GUI):
    """
    Status table widget for Photon Focus IMAQ camera.
    """
    def setup_status_table(self):
        self.add_num_label("frames_lost",formatter=("int"),label="Frames lost:")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "buffer_status" in params:
            bstat=params["buffer_status"]
            self.v["frames/buffstat"]="{:d} / {:d}".format(bstat.unread or 0,bstat.size or 0)
            self.v["frames_lost"]=bstat.lost



class PhotonFocusSiliconSoftwareCameraStatus_GUI(GenericCameraStatus_GUI):
    """
    Status table widget for Photon Focus SiliconSoftware camera.
    """
    def setup_status_table(self):
        self.add_num_label("frames_lost",formatter=("int"),label="Frames lost:")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "buffer_status" in params:
            bstat=params["buffer_status"]
            self.v["frames/buffstat"]="{:d} / {:d}".format(bstat.unread or 0,bstat.size or 0)
            self.v["frames_lost"]=bstat.lost



class UC480CameraStatus_GUI(GenericCameraStatus_GUI):
    """
    Status table widget for uc480 cameras.
    """
    def setup_status_table(self):
        self.add_num_label("frames_lost",formatter=("int"),label="Frames lost in transfer:")
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        super().show_parameters(params)
        if "acq_status" in params:
            acq_status=params["acq_status"]
            self.v["frames_lost"]=acq_status.transfer_missed