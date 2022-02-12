from pylablib.core.thread import controller
from pylablib.gui.widgets import range_controls


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
    
    def connect_updater(self, names):
        if not isinstance(names,(list,tuple)):
            names=[names]
        for n in names:
            self.base.vs[n].connect(self._update_value)
    def _update_value(self, v):
        self.settings.update_parameter_value(allow_diff_update=self.allow_diff_update)
        self._current_value=v
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
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
    """
    def __init__(self, settings, gui_name, label, default=None, indicator=False, cam_name=None):
        super().__init__(settings)
        self.gui_name=gui_name
        self.label=label
        self.default=default
        self.cam_name=cam_name or gui_name
        self.indicator=indicator
        self.disabled=False
        self.add_indicator=True
    def disable(self, disabled=True):
        self.disabled=disabled
        self.base.set_enabled(self.gui_name,not self.disabled)
    def add(self, base):
        super().add(base)
        if not self.indicator:
            self.connect_updater(self.gui_name)
    def setup(self, parameters, full_info):
        self.base.set_enabled(self.gui_name,self.cam_name in parameters)
    def to_camera(self, gui_value):
        """Convert widget value to camera parameter value"""
        return gui_value
    def from_camera(self, cam_value):
        """Convert camera parameter value to widget value"""
        return cam_value
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
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
    """
    def __init__(self, settings, gui_name, label, limit=(None,None), default=0, indicator=False, cam_name=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,cam_name=cam_name)
        self.limit=limit
    def add(self, base):
        if self.indicator:
            base.add_num_label(self.gui_name,value=self.default,label=self.label,formatter="int")
        else:
            base.add_num_edit(self.gui_name,value=self.default,label=self.label,limiter=self.limit+("coerce","int"),formatter="int")
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
        factor: factor used to convert between displayed and camera parameter values (``displayed=camera*factor``)
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
    """
    def __init__(self, settings, gui_name, label, limit=(None,None), fmt=".1f", default=0, indicator=False, factor=1, cam_name=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,cam_name=cam_name)
        self.limit=limit
        self.factor=factor
        self.fmt=fmt
    def add(self, base):
        if self.indicator:
            base.add_num_label(self.gui_name,value=self.default,label=self.label,formatter=self.fmt)
        else:
            base.add_num_edit(self.gui_name,value=self.default,label=self.label,limiter=self.limit+("coerce",),formatter=self.fmt,
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line"} if self.add_indicator=="next_line" else None)
        super().add(base)
    def to_camera(self, gui_value):
        return gui_value/self.factor
    def from_camera(self, cam_value):
        return cam_value*self.factor

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
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
    """
    def __init__(self, settings, gui_name, label, options, default=None, indicator=False, cam_name=None):
        super().__init__(settings,gui_name,label,default=default,indicator=indicator,cam_name=cam_name)
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
    def add(self, base):
        if self.indicator:
            base.add_text_label(self.gui_name,self.label,value=self._get_label(self.default))
        else:
            base.add_combo_box(self.gui_name,value=self.default,label=self.label,options=self.olabels,index_values=self.ovalues,
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line"} if self.add_indicator=="next_line" else None)
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
        cam_name: name of the parameter in the camera parameter dictionary (same as ``gui_name`` by default)
    """
    def _get_label(self, value):
        return "On" if value else "Off"
    def add(self, base):
        if self.indicator:
            base.add_text_label(self.gui_name,self.label,value=self._get_label(self.default))
        else:
            base.add_check_box(self.gui_name,self.label,value=bool(self.default),
                add_indicator=bool(self.add_indicator),location={"indicator":"next_line"} if self.add_indicator=="next_line" else None)
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
        self.cam_roi=None
    
    def add(self, base):
        self.base=base
        self.roi_ctl=range_controls.BinROICtl(base)
        self.roi_ctl.setup(xlim=(0,None),kind=self.roi_kind)
        self.roi_ctl.params.set_enabled("x_bin",self.bin_kind!="none")
        self.roi_ctl.params.set_enabled("y_bin",self.bin_kind not in {"same","none"})
        self.roi_ctl.set_value(((0,1E5,1),(0,1E5,1)))
        base.add_custom_widget("roi",self.roi_ctl)
        @controller.exsafeSlot()
        def _full_roi():
            xp,yp=self.roi_ctl.get_value()
            self.roi_ctl.set_value(((self.roi_ctl.xlim[0],self.roi_ctl.xlim[1],xp[2]),(self.roi_ctl.ylim[0],self.roi_ctl.ylim[1],yp[2])))
        base.add_button("set_full_roi","Full ROI",add_indicator=False,location=("next",2,1,1)).get_value_changed_signal().connect(lambda v: _full_roi())
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
        for n in ["roi","set_full_roi"]:
            base.vs[n].connect(self._update_value)
        self.cam_roi=None
    @controller.exsafe
    def on_changed(self):
        if self.cam_roi is not None:
            cam_ctl=self.settings.cam_ctl
            current_roi=self.roi_ctl.get_value()
            det_size=(self.roi_ctl.xlim[1],self.roi_ctl.ylim[1])
            if cam_ctl.preprocess_thread is not None:
                preprocessor=controller.sync_controller(cam_ctl.preprocess_thread)
                prep_bin=preprocessor.v["params/spat/bin"] if preprocessor.v["enabled"] else (1,1)
            else:
                prep_bin=(1,1)
            def _rel_span(src, dst):
                return dst[0]-src[0],dst[1]-src[0]
            full_bin=self.cam_roi[0][2]*prep_bin[1],self.cam_roi[1][2]*prep_bin[0]
            if self.bin_kind=="same":
                full_bin=full_bin[0],full_bin[0]
            x_cam_span=self.cam_roi[0][0]/full_bin[0],self.cam_roi[0][1]/full_bin[0]
            y_cam_span=self.cam_roi[1][0]/full_bin[1],self.cam_roi[1][1]/full_bin[1]
            x_gui_span=current_roi[0][0]/full_bin[0],current_roi[0][1]/full_bin[0]
            y_gui_span=current_roi[1][0]/full_bin[1],current_roi[1][1]/full_bin[1]
            x_rel_span=_rel_span(x_cam_span,x_gui_span)
            y_rel_span=_rel_span(y_cam_span,y_gui_span)
            center=(y_rel_span[0]+y_rel_span[1])/2,(x_rel_span[0]+x_rel_span[1])/2
            size=y_rel_span[1]-y_rel_span[0],x_rel_span[1]-x_rel_span[0]
            cam_ctl.plot_control("rectangles/set",("new_roi",center,size))
            cam_ctl.plot_control("rectangles/"+("show" if self.settings.v["show_gui_roi"] else "hide"),("new_roi",))
            x_det_span=(0,det_size[0]/full_bin[0])
            y_det_span=(0,det_size[1]/full_bin[1])
            x_rel_span=_rel_span(x_cam_span,x_det_span)
            y_rel_span=_rel_span(y_cam_span,y_det_span)
            center=(y_rel_span[0]+y_rel_span[1])/2,(x_rel_span[0]+x_rel_span[1])/2
            size=y_rel_span[1]-y_rel_span[0],x_rel_span[1]-x_rel_span[0]
            cam_ctl.plot_control("rectangles/set",("det_size",center,size))
            cam_ctl.plot_control("rectangles/"+("show" if self.settings.v["show_det_size"] else "hide"),("det_size",))

    def setup(self, parameters, full_info):
        if not all(p in parameters for p in ["roi","roi_limits"]):
            self.base.set_enabled(["roi","roi_indicator"],False)
        else:
            hlim,vlim=parameters["roi_limits"]
            maxbin=max(hlim.maxbin,vlim.maxbin)
            self.roi_ctl.set_limits(xlim=(0,hlim.max),ylim=(0,vlim.max),minsize=(hlim.min,vlim.min),maxbin=maxbin)
    def collect(self, parameters):
        xroi,yroi=self.settings.v["roi"]
        roi_len={"both":6,"same":5,"none":4}[self.bin_kind]
        parameters["roi"]=(xroi.min,xroi.max,yroi.min,yroi.max,xroi.bin,yroi.bin)[:roi_len]
        super().collect(parameters)
    def display(self, parameters):
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
        self.cam_roi=(roi[0],roi[1],(roi[4] if len(roi)>4 else 1)),(roi[2],roi[3],(roi[5] if len(roi)>5 else 1))
        self.on_changed()
        super().display(parameters)