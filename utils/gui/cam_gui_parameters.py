from pylablib.core.thread import controller
from pylablib.gui.widgets import range_controls

import numpy as np

class IGUIParameter:
    """
    A generic camera settings parameter.
    
    Controls creating and setup of the corresponding widgets depending on the camera parameters,
    and reading and displaying the parameter values.

    Args:
        settings: base settings widget
    """
    def __init__(self, settings):
        self.settings=settings
        self.allow_diff_update=False
        self._current_value=None
    
    def connect_updater(self, names):
        if not isinstance(names,(list,tuple)):
            names=[names]
        for n in names:
            self.base.vs[n].connect(controller.exsafe(self._update_value))
    def _is_diff_update_allowed(self, oldv, newv):
        return self.allow_diff_update
    def _update_value(self, v):
        self.settings.update_parameter_value(allow_diff_update=self._is_diff_update_allowed(self._current_value,v))
        self._current_value=v
    def on_set_all_values(self, values):
        """
        Set all values given the dictionary.
        
        Note that after this method a regular GUI ``set_all_values`` method is used, which may overwrite some of the applied changes.
        However, the dictionary can be modified to affect later changes.
        """
    def on_connection_changed(self, connected):
        """Notify that the camera has just been connected or disconnected"""
    def add(self, base):
        """Add the parameter to the given base widget (a parameter table)"""
        self.base=base
    def setup(self, parameters, full_info):
        """Setup the parameter given all the camera parameters and the full info"""
    def collect(self, parameters):
        """Add the widget value to the given parameters dictionary"""
    def display(self, parameters):
        """Display the parameter value from the given parameters dictionary"""


class SingleGUIParameter(IGUIParameter):
    """
    Simple single-value GUI parameter.

    Base class for float, int, combo box, or check box parameters.

    Args:
        settings: base settings widget
        gui_name: name of the corresponding widget
        label: widget label
        default: default value
        indicator: if ``True``, the widget is simply an indicator and can not control the parameter
        add_indicator: whether add indicator to this parameter
        indirect: whether the parameter is "indirect", i.e., does not directly relate to a camera parameter; in this case it is still added to the parameters dictionary,
            but is not disabled when the parameter is missing
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
        to_camera: custom method to convert GUI value to camera value
        from_camera: custom method to convert camera value to GUI value
    """
    def __init__(self, settings, gui_name, label, default=None, indicator=False, add_indicator=True, indirect=False, cam_name=None, to_camera=None, from_camera=None):
        super().__init__(settings)
        self.gui_name=gui_name
        self.label=label
        self.default=default
        self.cam_name=cam_name or gui_name
        self.indicator=indicator
        self.disabled=False
        self.indirect=indirect
        self.add_indicator=add_indicator
        self.from_camera_func=from_camera
        self.to_camera_func=to_camera
    def disable(self, disabled=True):
        self.disabled=disabled
        self.base.set_enabled(self.gui_name,not self.disabled)
    def add(self, base):
        super().add(base)
        if not self.indicator:
            self.connect_updater(self.gui_name)
    def setup(self, parameters, full_info):
        self.base.set_enabled(self.gui_name,self.cam_name in parameters or self.indirect)
    def to_camera(self, gui_value):
        """Convert widget value to camera parameter value"""
        return self.to_camera_func(gui_value) if self.to_camera_func else gui_value
    def from_camera(self, cam_value):
        """Convert camera parameter value to widget value"""
        return self.from_camera_func(cam_value) if self.from_camera_func else cam_value
    def collect(self, parameters):
        if not self.disabled:
            parameters[self.cam_name]=self.to_camera(self.settings.v[self.gui_name])
    def display(self, parameters):
        if self.cam_name in parameters and not self.disabled:
            if self.indicator:
                self.settings.v[self.gui_name]=self.from_camera(parameters[self.cam_name])
            elif self.add_indicator:
                self.settings.i[self.gui_name]=self.from_camera(parameters[self.cam_name])



class IntGUIParameter(SingleGUIParameter):
    """
    Simple integer GUI parameter.

    Args:
        settings: base settings widget
        gui_name: name of the corresponding widget
        label: widget label
        limit: value limit tuple (``None`` means no limit)
        default: default value
        indicator: if ``True``, the widget is simply an indicator and can not control the parameter
        add_indicator: whether add indicator to this parameter
        indirect: whether the parameter is "indirect", i.e., does not directly relate to a camera parameter; in this case it is still added to the parameters dictionary,
            but is not disabled when the parameter is missing
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
        to_camera: custom method to convert GUI value to camera value
        from_camera: custom method to convert camera value to GUI value
    """
    def __init__(self, settings, gui_name, label, limit=(None,None), default=0, indicator=False, add_indicator=True, indirect=False, cam_name=None, to_camera=None, from_camera=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,add_indicator=add_indicator,indirect=indirect,
            cam_name=cam_name,to_camera=to_camera,from_camera=from_camera)
        self.limit=limit
    def add(self, base, row=None):
        if row is not None:
            if row<0:
                row%=base.get_layout_shape()[0]
            base.insert_row(row)
        if self.indicator:
            base.add_num_label(self.gui_name,value=self.default,label=self.label,formatter="int",location=row)
        else:
            base.add_num_edit(self.gui_name,value=self.default,label=self.label,limiter=self.limit+("coerce","int"),formatter="int",
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line","widget":row} if self.add_indicator=="next_line" else row)
        super().add(base)

class FloatGUIParameter(SingleGUIParameter):
    """
    Simple floating point GUI parameter.

    Args:
        settings: base settings widget
        gui_name: name of the corresponding widget
        label: widget label
        limit: value limit tuple (``None`` means no limit)
        fmt: value format
        default: default value
        indicator: if ``True``, the widget is simply an indicator and can not control the parameter
        add_indicator: whether add indicator to this parameter
        indirect: whether the parameter is "indirect", i.e., does not directly relate to a camera parameter; in this case it is still added to the parameters dictionary,
            but is not disabled when the parameter is missing
        factor: factor used to convert between displayed and camera parameter values (``displayed=camera*factor``)
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
        to_camera: custom method to convert GUI value to camera value
        from_camera: custom method to convert camera value to GUI value
    """
    def __init__(self, settings, gui_name, label, limit=(None,None), fmt=".1f", default=0, indicator=False, add_indicator=True, indirect=False, factor=1, cam_name=None, to_camera=None, from_camera=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,add_indicator=add_indicator,indirect=indirect,
            cam_name=cam_name,to_camera=to_camera,from_camera=from_camera)
        self.limit=limit
        self.factor=factor
        self.fmt=fmt
    def add(self, base, row=None):
        if row is not None:
            if row<0:
                row%=base.get_layout_shape()[0]
            base.insert_row(row)
        if self.indicator:
            base.add_num_label(self.gui_name,value=self.default,label=self.label,formatter=self.fmt,location=row)
        else:
            base.add_num_edit(self.gui_name,value=self.default,label=self.label,limiter=self.limit+("coerce",),formatter=self.fmt,
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line","widget":row} if self.add_indicator=="next_line" else row)
        super().add(base)
    def to_camera(self, gui_value):
        return self.to_camera_func(gui_value) if self.to_camera_func else gui_value/self.factor
    def from_camera(self, cam_value):
        return self.from_camera_func(cam_value) if self.from_camera_func else cam_value*self.factor

class EnumGUIParameter(SingleGUIParameter):
    """
    Simple enumerated GUI parameter, which is represented by a combo box.

    Args:
        settings: base settings widget
        gui_name: name of the corresponding widget
        label: widget label
        options: dictionary ``{value: label}`` with the possible parameter values
        default: default value (``None`` means the first option).
        indicator: if ``True``, the widget is simply an indicator and can not control the parameter
        add_indicator: whether add indicator to this parameter
        indirect: whether the parameter is "indirect", i.e., does not directly relate to a camera parameter; in this case it is still added to the parameters dictionary,
            but is not disabled when the parameter is missing
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
        to_camera: custom method to convert GUI value to camera value
        from_camera: custom method to convert camera value to GUI value
    """
    def __init__(self, settings, gui_name, label, options, default=None, indicator=False, add_indicator=True, indirect=False, cam_name=None, to_camera=None, from_camera=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,add_indicator=add_indicator,indirect=indirect,
            cam_name=cam_name,to_camera=to_camera,from_camera=from_camera)
        if isinstance(options,(list,tuple)):
            options=dict(enumerate(options))
        self.options=options
        self.ovalues=list(self.options)
        self.olabels=[self.options[v] for v in self.ovalues]
        self.coerce=True
    def _get_label(self, value):
        if value is None:
            return self.olabels[0]
        try:
            return self.options[value]
        except KeyError:
            if self.coerce:
                return self.olabels[0]
            raise ValueError(value)
    def add(self, base, row=None):
        if row is not None:
            if row<0:
                row%=base.get_layout_shape()[0]
            base.insert_row(row)
        if self.indicator:
            base.add_text_label(self.gui_name,self.label,value=self._get_label(self.default))
        else:
            base.add_combo_box(self.gui_name,value=self.default,label=self.label,options=self.olabels,index_values=self.ovalues,
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line","widget":row} if self.add_indicator=="next_line" else row)
        super().add(base)
    def display(self, parameters):
        try:
            super().display(parameters)
        except ValueError:
            if self.coerce:
                super().display({self.gui_name:self.ovalues[0]})
            else:
                raise
    def from_camera(self, cam_value):
        return self._get_label(cam_value) if self.indicator else super().from_camera(cam_value)

class BoolGUIParameter(SingleGUIParameter):
    """
    Simple boolean GUI parameter, which is represented by a check box.

    Args:
        settings: base settings widget
        gui_name: name of the corresponding widget
        label: widget label
        default: default value.
        indicator: if ``True``, the widget is simply an indicator and can not control the parameter
        add_indicator: whether add indicator to this parameter
        indirect: whether the parameter is "indirect", i.e., does not directly relate to a camera parameter; in this case it is still added to the parameters dictionary,
            but is not disabled when the parameter is missing
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
        to_camera: custom method to convert GUI value to camera value
        from_camera: custom method to convert camera value to GUI value
    """
    def _get_label(self, value):
        return "On" if value else "Off"
    def add(self, base, row=None):
        if row is not None:
            if row<0:
                row%=base.get_layout_shape()[0]
            base.insert_row(row)
        if self.indicator:
            base.add_text_label(self.gui_name,self.label,value=self._get_label(self.default))
        else:
            base.add_check_box(self.gui_name,self.label,value=bool(self.default),
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line","widget":row} if self.add_indicator=="next_line" else row)
        super().add(base)
    def from_camera(self, cam_value):
        return self._get_label(cam_value) if self.indicator else super().from_camera(cam_value)





class ROIGUIParameter(IGUIParameter):
    """
    ROI GUI parameter.

    Includes several widgets: ROI controller, frame showing buttons, roi indicator, and image size indicator.

    Args:
        settings: base settings widget
        bin_kind: binning kind; can be ``none`` (no binning), ``same`` (same for both axes), or ``both`` (different on both axes)
        roi_kind: roi setting kind; can be ``minmax`` or ``minsize``.s
    """
    def __init__(self, settings, bin_kind="none", roi_kind="minmax"):
        super().__init__(settings)
        self.bin_kind=bin_kind
        self.roi_kind=roi_kind
        self.detector_size=None
    
    def add(self, base):
        self.base=base
        self.roi_ctl=range_controls.BinROICtl(base)
        self.roi_ctl.setup(xlim=(0,None),kind=self.roi_kind)
        self.roi_ctl.params.set_enabled("x_bin",self.bin_kind!="none")
        self.roi_ctl.params.set_enabled("y_bin",self.bin_kind not in {"same","none"})
        self.roi_ctl.set_value(((0,1E5,1),(0,1E5,1)))
        base.add_custom_widget("roi",self.roi_ctl)
        with base.using_new_sublayout("roi_buttons","hbox",location=("next",0,1,"end")):
            @controller.exsafe
            def _select_roi(v):
                if "plotter_area" in self.settings.cam_ctl.c:
                    self.settings.cam_ctl.c["plotter_area"].enable_selection_frame(v,image_bound=False)
                    self._switch_to_standard_tab(v)
            base.add_toggle_button("select_roi","Select in image",add_indicator=False,location=("next",2,1,1)).get_value_changed_signal().connect(_select_roi)
            base.add_padding()
            @controller.exsafe
            def _full_roi():
                xp,yp=self.roi_ctl.get_value()
                self.roi_ctl.set_value(((self.roi_ctl.xlim[0],self.roi_ctl.xlim[1],xp[2]),(self.roi_ctl.ylim[0],self.roi_ctl.ylim[1],yp[2])))
            base.add_button("set_full_roi","Maximize",add_indicator=False,location=("next",2,1,1)).get_value_changed_signal().connect(_full_roi)
        with base.using_new_sublayout("show_rectangles","hbox",location=("next",0,1,"end")):
            base.add_check_box("show_gui_roi","Show selected ROI",add_indicator=False)
            base.add_check_box("show_det_size","Show full frame",add_indicator=False)
        base.add_spacer(5)
        with base.using_new_sublayout("roi_labels","grid",location=("next",0,1,"end")):
            base.add_text_label("roi_indicator",label="ROI")
            base.add_text_label("size_indicator",label="Image size")
            base.get_sublayout().setColumnStretch(1,1)
        for n in ["roi","show_gui_roi","show_det_size"]:
            base.vs[n].connect(lambda v: self.on_changed())
        for n in ["show_gui_roi","show_det_size"]:
            base.vs[n].connect(self._switch_to_standard_tab)
        base.vs["roi"].connect(controller.exsafe(self._update_value))
        if "plotter_area" in self.settings.cam_ctl.c:
            self.settings.cam_ctl.c["plotter_area"].frame_selected.connect(self.on_roi_select)
    @controller.exsafe
    def on_roi_select(self):
        p1,p2=self.settings.cam_ctl.c["plotter_area"].get_selection_frame("frame")
        p1,p2=np.sort([p1,p2],axis=0).astype("int")
        xp,yp=self.roi_ctl.get_value()
        self.roi_ctl.set_value(((p1[0],p2[0],xp[2]),(p1[1],p2[1],yp[2])))
        self.base.v["select_roi"]=False
    @controller.exsafe
    def on_changed(self):
        if self.detector_size is not None:
            cam_ctl=self.settings.cam_ctl
            current_roi=self.roi_ctl.get_value()
            current_roi_size=np.array([current_roi[0][1]-current_roi[0][0],current_roi[1][1]-current_roi[1][0]])
            current_roi_center=np.array([current_roi[0][1]+current_roi[0][0],current_roi[1][1]+current_roi[1][0]])/2
            cam_ctl.plot_control("rectangles/set",("new_roi",current_roi_center,current_roi_size))
            cam_ctl.plot_control("rectangles/"+("show" if self.settings.v["show_gui_roi"] else "hide"),("new_roi",))
            det_size=(self.roi_ctl.xlim[1],self.roi_ctl.ylim[1])
            full_roi_size=np.array(det_size)
            full_roi_center=np.array(det_size)/2
            cam_ctl.plot_control("rectangles/set",("full_roi",full_roi_center,full_roi_size))
            cam_ctl.plot_control("rectangles/"+("show" if self.settings.v["show_det_size"] else "hide"),("full_roi",))
    @controller.exsafe
    def _switch_to_standard_tab(self, show=True):
        if show:
            self.settings.cam_ctl.ctl.call_thread_method("toggle_tab","plot_tabs","standard_frame")

    def setup(self, parameters, full_info):
        if not all(p in parameters for p in ["roi","roi_limits"]):
            self.base.set_enabled(["roi","roi_indicator"],False)
        else:
            hlim,vlim=parameters["roi_limits"]
            maxbin=max(hlim.maxbin,vlim.maxbin)
            self.roi_ctl.set_limits(xlim=(0,hlim.max),ylim=(0,vlim.max),minsize=(hlim.min,vlim.min),maxbin=maxbin)
            self.detector_size=(hlim.max,vlim.max)
    def on_set_all_values(self, values):
        if "select_roi" in values:
            del values["select_roi"]
    def collect(self, parameters):
        xroi,yroi=self.settings.v["roi"]
        roi_len={"both":6,"same":5,"none":4}[self.bin_kind]
        parameters["roi"]=(xroi.min,xroi.max,yroi.min,yroi.max,xroi.bin,yroi.bin)[:roi_len]
        super().collect(parameters)
    def display(self, parameters):
        if "roi" not in parameters:
            return
        roi=parameters["roi"]
        roi_str="[{:d} - {:d}] x [{:d} - {:d}]".format(*roi)
        if self.bin_kind=="same":
            roi_str+="  Bin {:d}".format(roi[4])
        elif self.bin_kind=="both":
            roi_str+="  Bin {:d}x{:d}".format(*roi[4:6])
        self.settings.v["roi_indicator"]=roi_str
        xbin=roi[4] if len(roi)>4 else 1
        ybin=roi[5] if len(roi)>5 else xbin
        size_str="{:d} x {:d}".format((roi[1]-roi[0])//xbin,(roi[3]-roi[2])//ybin)
        self.settings.v["size_indicator"]=size_str
        super().display(parameters)




class AttributesBrowserGUIParameter(IGUIParameter):
    def __init__(self, settings, browser_class):
        super().__init__(settings)
        self.browser_class=browser_class
    def _show_window(self, visible=True):
        if visible:
            if not self.window.isVisible():
                self.window.showNormal()
            else:
                self.window.show()
        else:
            self.window.hide()
    def add(self, base):
        self.base=base
        self.window=self.browser_class(self.base)
        self.window.setup(self.settings.cam_ctl)
        self.base.add_button("show_attributes_window","Show attributes",add_indicator=False).get_value_changed_signal().connect(lambda: self._show_window())
        self.base.add_child("attributes_window",self.window,location="skip",gui_values_path="attributes_window")
        self._connected=False
        self._startup_done=False

    def setup(self, parameters, full_info):
        self.window.setup_parameters(full_info)
        self.window.finalize_setup()
    def on_connection_changed(self, connected):
        self._connected=connected
        self._startup_done=False
    def display(self, parameters):
        if self._connected and not self._startup_done and parameters.get("tag/initialized",False):
            self.window.setup_startup()
            self._startup_done=True
        self.window.update_attributes()
        super().display(parameters)