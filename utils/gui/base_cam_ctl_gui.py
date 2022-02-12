from pylablib.core.thread import controller
from pylablib.core.gui.widgets import container, param_table
from pylablib.gui.widgets import range_controls

from . import cam_gui_parameters
from .cam_gui_parameters import IntGUIParameter, FloatGUIParameter, BoolGUIParameter, EnumGUIParameter, ROIGUIParameter


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
    def __init__(self, parent=None, name=None, cam_desc=None):
        super().__init__(parent=parent, name=name)
        self.cam_desc=cam_desc
    def setup(self, ctl):
        super().setup(no_margins=True)
        self.cam_ctl=ctl
        self._default_values=None
        self._gui_parameters=[]
        self._roi_kind=self.cam_ctl.settings.get("interface/cam_control/roi_kind",self._roi_kind)
        settings_tabs=self.add_child("settings_tabs",container.QTabContainer(self))
        settings_tabs.setup()
        self.common_params=settings_tabs.add_tab("common","Common").add_child("common_params",param_table.ParamTable(self))
        self.common_params.setup(add_indicator=True)
        self.advanced_params=settings_tabs.add_tab("advanced","Advanced").add_child("advanced_params",param_table.ParamTable(self))
        self.advanced_params.setup(add_indicator=True)
        # Setup camera settings table
        self.setup_settings_tables()
        self.common_params.add_padding()
        self.advanced_params.add_padding()
        self.common_params.update_indicators()
        self.advanced_params.update_indicators()
        self.settings_params=self.add_child("settings_params",param_table.ParamTable(self))
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
        @controller.exsafe
        def on_auto_apply(v):
            if v:
                self.send_parameters()
        self.settings_params.vs["auto_apply"].connect(on_auto_apply)
        self.settings_params.layout().setColumnStretch(1,0)
        self._setup_done=False
        self.setEnabled(False)

    def update_parameter_value(self, allow_diff_update=False):
        if self.v["auto_apply"]:
            self.cam_ctl.send_parameters(only_diff=allow_diff_update,dependencies=self._param_dependencies)

    def _get_tab(self, tab):
        if tab=="common":
            return self.common_params
        if tab=="advanced":
            return self.advanced_params
        raise ValueError("unrecognized tab: {}".format(tab))
    def add_parameter(self, param, tab):
        """Add the given parameter to the given tab (``"common"`` or ``"advanced"``)"""
        param.add(self._get_tab(tab))
        self._gui_parameters.append(param)
    def setup_settings_tables(self):
        """Setup settings table entries"""
    # Build a dictionary of camera parameters from the controls
    def collect_parameters(self):
        """Get camera parameters as a dictionary"""
        parameters={}
        for p in self._gui_parameters:
            p.collect(parameters)
        return parameters
    # Setup interface limits according to camera parameters
    def setup_gui_parameters(self, parameters, full_info):
        """Setup sub-widgets appearance"""
        if parameters["status/connection"]!="opened":
            return
        self.setEnabled(True)
        for p in self._gui_parameters:
            p.setup(parameters,full_info)
        self._setup_done=True
        if self._default_values is not None:
            super().set_all_values(self._default_values)
    # Update the interface indicators according to camera parameters
    def show_parameters(self, parameters):
        """Set camera parameter indicators"""
        for p in self._gui_parameters:
            p.display(parameters)
    def set_all_values(self, value):
        self._default_values=value.copy()
        return super().set_all_values(value)
    def get_all_values(self):
        return super().get_all_values() if self._setup_done else self._default_values






class GenericCameraSettings_GUI(ICameraSettings_GUI):
    """
    Settings table widget for a generic camera.

    Defines most common controls: exposue, ROI, trigger mode.
    Other settings tables inherit from this one.
    """
    _frame_period_kind="none"
    _roi_kind="minmax"
    _bin_kind="none"
    _trigger_modes={"int":"Internal","ext":"External"}
    def get_basic_parameters(self, name):
        """Get basic GUI parameters, which can be shared between different cameras"""
        if name=="exposure": return FloatGUIParameter(self,"exposure","Exposure (ms)",limit=(0,None),fmt=".2f",default=100,factor=1E3)
        if name=="frame_period":
            if self._frame_period_kind=="none":
                return
            indicator=self._frame_period_kind=="indicator"
            return FloatGUIParameter(self,"frame_period","Frame period (ms)",limit=(0,None),fmt=".2f",default=0,factor=1E3,indicator=indicator)
        if name=="roi": return ROIGUIParameter(self,bin_kind=self._bin_kind,roi_kind=self._roi_kind)
        if name=="trigger_mode": return EnumGUIParameter(self,"trigger_mode","Trigger mode",self._trigger_modes)
        if name=="add_info":
            parameter=BoolGUIParameter(self,"add_info","Acquire frame info")
            parameter.allow_diff_update=True
            return parameter
    def add_builtin_parameter(self, name, tab):
        parameter=self.get_basic_parameters(name)
        if parameter is not None:
            self.add_parameter(parameter,tab)
    def setup_settings_tables(self):
        self.add_builtin_parameter("exposure","common")
        self.add_builtin_parameter("frame_period","common")
        self.add_builtin_parameter("roi","common")
        self.add_builtin_parameter("trigger_mode","advanced")
        self.add_builtin_parameter("add_info","advanced")







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
    def __init__(self, parent=None, name=None, cam_desc=None):
        super().__init__(parent=parent, name=name)
        self.cam_desc=cam_desc
    def setup(self, ctl):
        param_table.StatusTable.setup(self,"status_table")
        self.cam_ctl=ctl
        with self.using_new_sublayout("header","grid"):
            self.add_text_label("cam_name",label="Name:  ")
            self.w["cam_name"].setMaximumWidth(180)
            self.add_text_label("cam_kind",label="Kind:  ")
            self.w["cam_kind"].setMaximumWidth(180)
            self.add_padding("horizontal",location=(0,"next"),stretch=1)
        if self.cam_desc is not None:
            self.v["cam_kind"],self.v["cam_name"]=self.cam_desc.get_camera_labels()
        self.add_spacer(5)
        def set_connection_style(v):
            self.w["connection"].setStyleSheet("background: gold; font-weight: bold; color: black" if v=="Disconnected" else "")
        self.add_status_line("connection",label="Connection:",srcs=self.cam_ctl.cam_thread,tags="status/connection_text")
        self.vs["connection"].connect(set_connection_style)
        self.update_status_line("connection")
        self.add_status_line("acquisition",label="Acquisition:",srcs=self.cam_ctl.cam_thread,tags="status/acquisition_text")
        self.update_status_line("acquisition")
        self.add_num_label("frames/acquired",formatter="int",label="Frames acquired:")
        self.add_num_label("frames/read",formatter="int",label="Frames read:")
        self.add_text_label("frames/buffstat",label="Buffer fill status:")
        self.add_num_label("frames/fps",formatter=".2f",label="FPS:")
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