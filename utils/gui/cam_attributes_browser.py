from pylablib.core.gui import QtWidgets, QtCore, Signal
from pylablib.core.thread.controller import exsafe, add_exception_hook

from pylablib import widgets

import collections

TAttribute=collections.namedtuple("TAttribute",["kind","attribute","indicator","widgets","rng"])
class CamAttributesBrowser(widgets.QWidgetContainer):
    def setup(self, cam_ctl):
        super().setup()
        self.cam_ctl=cam_ctl
        self.camera=None
        self.setWindowTitle("Camera attributes")
        self.setWindowFlag(QtCore.Qt.Dialog)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint,False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint,False)
        self.tabs=self.add_child("tabs",widgets.QTabContainer(self))
        self.values_tab=self.tabs.add_tab("value","Values",widget=widgets.ParamTable(self))
        self.values_tab.setup()
        self.values_scroll_area=self.values_tab.add_child("scroll_area",widgets.QScrollAreaContainer(self))
        self.values_scroll_area.setup()
        self.values_scroll_area.verticalScrollBar().valueChanged.connect(lambda: self._move_scroll(self.values_scroll_area))
        values_widget=self.values_scroll_area.widget()
        self.params_table=values_widget.add_child("params",widgets.ParamTable(values_widget))
        self.params_table.setup(add_indicator=True)
        for i in range(5):
            self.params_table.add_spacer(0,70,location=(0,i,1,1))
        self.params_table.add_spacer(5)
        self.params_table.add_decoration_label("Attribute",location=(0,0))
        self.params_table.add_decoration_label("To set",location=(0,1))
        self.params_table.add_decoration_label("Current",location=(0,3))
        self.props_tab=self.tabs.add_tab("value_props","Settings",widget=widgets.ParamTable(self))
        self.props_tab.setup()
        self.props_scroll_area=self.props_tab.add_child("scroll_area",widgets.QScrollAreaContainer(self))
        self.props_scroll_area.setup()
        self.props_scroll_area.verticalScrollBar().valueChanged.connect(lambda: self._move_scroll(self.props_scroll_area))
        props_widget=self.props_scroll_area.widget()
        self.props_table=props_widget.add_child("params",widgets.ParamTable(props_widget))
        self.props_table.setup(add_indicator=False)
        self.props_table.add_decoration_label("Attribute",location=(0,0))
        self.props_table.add_decoration_label("On set",location=(0,1))
        self.props_table.add_decoration_label("Autoset",location=(0,2))
        self.props_table.add_decoration_label("Quick access",location=(0,3))
        for i,w in enumerate([70,70,70,70,20]):
            self.props_table.add_spacer(0,w,location=(0,i,1,1))
        self.props_table.add_spacer(5)
        self.props_table.set_column_stretch([0,0,0,0,1])
        self.buttons=self.add_child("buttons",widgets.ParamTable(self))
        self.buttons.setup(add_indicator=False)
        with self.buttons.using_new_sublayout("buttons","hbox"):
            self.buttons.add_check_box("quick_access","Show quick access only",value=False)
            self.buttons.vs["quick_access"].connect(self.setup_visibility)
            self.buttons.add_padding()
            self.buttons.add_button("close","Close")
            self.w["close"].setFixedWidth(100)
            self.buttons.vs["close"].connect(self.close)
        self.add_property_element("window/size",
            lambda: (self.size().width(),self.size().height()), lambda v: self.resize(*v), add_indicator=False)
        self._attributes={}
        self._cam_setup_done=False
        self._activity_state="off"
        self._autoset_paused=False
        self._sync_values=set()
        self._error_raised=False
        self._initial_values={}
        add_exception_hook("{}_camera_attributes_window".format(self.cam_ctl.cam_thread),self._on_error)
        self.activate(False)

    def _on_error(self):
        self._error_raised=True
    def _on_parameters_updated(self, *_):
        self._activity_state="updated" if self._activity_state=="activated" else self._activity_state

    def _setup_connected_camera(self):
        if not self._cam_setup_done:
            self.ctl.subscribe_direct(self._on_parameters_updated,srcs=self.cam_ctl.dev.name,tags="changed/parameters")
        self.cam_ctl.dev.ca.set_camera_attributes_error_action("report")
        self._cam_setup_done=True

    closed=Signal()
    @exsafe
    def closeEvent(self, event):
        self.closed.emit()
        return super().closeEvent(event)
    @exsafe
    def _move_scroll(self, src):
        p=src.verticalScrollBar().value()
        for w in [self.values_scroll_area,self.props_scroll_area]:
            if w.verticalScrollBar().value()!=p:
                w.verticalScrollBar().setValue(p)
    def showEvent(self, event):
        self.activate(True)
        return super().showEvent(event)
    def hideEvent(self, event):
        self.activate(False)
        return super().hideEvent(event)
    

    def _add_dummy_checkbox(self, table, location=-1):
        w=QtWidgets.QCheckBox("",parent=self.params_table)  # dummy checkbox as a workaround for aligning tabs layouts
        w.setObjectName("dummy")
        p=w.sizePolicy()
        p.setRetainSizeWhenHidden(True)
        w.setSizePolicy(p)
        table.add_to_layout(w,location=(location,0,1,1))
        w.hide()
        return w
    def decorate_parameter(self, name, label, indicator=False):
        """Add common parameter items: set button, properties, error indicators, etc."""
        att=self._attributes[name]
        att.widgets.append(self._add_dummy_checkbox(self.params_table))
        att.widgets.append(self.props_table.add_decoration_label(label))
        if not indicator:
            self.params_table.add_button("s/"+name,caption="Set",add_indicator=False,location=(-1,2,1,1))
            self.params_table.add_text_label("e/"+name,location=(-1,4,1,1))
            self.params_table.w["e",name].setAlignment(QtCore.Qt.AlignCenter)
            self.params_table.w["e",name].clicked.connect(lambda: self._clear_error_indicator(name))
            self.props_table.add_combo_box("p_pause/"+name,options={"none":"None","restart":"Restart","clear":"Clear"},value="clear",location=(-1,1,1,1))
            self.props_table.add_combo_box("p_autoset/"+name,options={"never":"Never","startup":"Startup","always":"Always"},location=(-1,2,1,1))
            self.params_table.vs["s",name].connect(lambda: self._set_camera_attributes(name))
            self.params_table.vs["v",name].connect(lambda: self._on_change_attribute(name))
            att.widgets.append(self.params_table.w["e",name])
            att.widgets.append(self.params_table.w["s",name])
            att.widgets.append(self.props_table.w["p_pause",name])
            att.widgets.append(self.props_table.w["p_autoset",name])
        self.props_table.add_check_box("p_quick/"+name,caption="",location=(-1,3,1,1))
        att.widgets.append(self.props_table.w["p_quick",name])
    def _parloc(self, indicator):
        return {"widget":("next",2,1,3),"label":("next",0)} if indicator else {"widget":("next",0,1,2),"indicator":("next",3)}
    def add_bool_parameter(self, name, label, default=False, indicator=False):
        """Add a boolean attribute row"""
        if indicator:
            self.params_table.add_enum_label("v/"+name,value=default,options={False:"Off",True:"On"},prep=bool,label=label,location=self._parloc(indicator))
        else:
            self.params_table.add_check_box("v/"+name,"",value=default,label=label,location=self._parloc(indicator))
        self.decorate_parameter(name,label,indicator=indicator)
    def add_choice_parameter(self, name, label, options, default=None, indicator=False):
        """Add a enum attribute row"""
        options=options if isinstance(options,dict) else dict(zip(range(len(options)),options))
        ovals,olabels=list(zip(*options.items()))
        if default is None:
            default=ovals[0]
        if indicator:
            self.params_table.add_enum_label("v/"+name,value=default,options=options,label=label,out_of_range="ignore",location=self._parloc(indicator))
        else:
            self.params_table.add_combo_box("v/"+name,value=default,label=label,options=olabels,index_values=ovals,out_of_range="ignore",location=self._parloc(indicator))
        self.decorate_parameter(name,label,indicator=indicator)
    def add_integer_parameter(self, name, label, limits=(0,None), default=0, indicator=False):
        """Add an integer attribute row"""
        if indicator:
            self.params_table.add_num_label("v/"+name,value=default,label=label,limiter=limits+("coerce","int"),formatter="int",location=self._parloc(indicator))
        else:
            self.params_table.add_num_edit("v/"+name,value=default,label=label,limiter=limits+("coerce","int"),formatter="int",location=self._parloc(indicator))
        self.decorate_parameter(name,label,indicator=indicator)
    def add_string_parameter(self, name, label, default="", indicator=False):
        """Add a string attribute row"""
        if indicator:
            self.params_table.add_text_label("v/"+name,value=default,label=label,location=self._parloc(indicator))
        else:
            self.params_table.add_text_edit("v/"+name,value=default,label=label,location=self._parloc(indicator))
        self.decorate_parameter(name,label,indicator=indicator)
    def add_float_parameter(self, name, label, limits=(0,None), fmt=".3f", default=0, indicator=False):
        """Add a float attribute row"""
        if indicator:
            self.params_table.add_num_label("v/"+name,value=default,label=label,limiter=limits,formatter=fmt,location=self._parloc(indicator))
        else:
            self.params_table.add_num_edit("v/"+name,value=default,label=label,limiter=limits,formatter=fmt,location=self._parloc(indicator))
        self.decorate_parameter(name,label,indicator=indicator)


    def _record_attribute(self, name, kind, attribute, indicator=False, rng=None):
        self._attributes[name]=TAttribute(kind,attribute,indicator,[],[rng])
    def _add_attribute(self, name, attribute, value):
        pass
    def setup_parameters(self, full_info):
        """Setup parameter rows"""
        if "camera_attributes_desc" in full_info:
            for n,a in full_info["camera_attributes_desc"].items(leafs=True,path_kind="joined"):
                self._add_attribute(n,a,value=full_info.get(("camera_attributes",n),None))
    def finalize_setup(self):
        """Finalize the setup: set up borders, sizes, etc."""
        self.params_table.pad_borders()
        self.props_table.pad_borders()
        self.tabs.setCurrentIndex(1)
        self.show()
        self.setMinimumHeight(300)
        self.hide()
        self.tabs.setCurrentIndex(0)
        self.setup_visibility()
    def _get_attribute_range(self, attribute):
        return None
    def _update_parameter_range(self, name, attribute):
        rng=self._get_attribute_range(attribute)  # pylint: disable=assignment-from-none
        if name in self._attributes and rng is not None and self._attributes[name].rng[0]!=rng:
            if self._attributes[name].kind=="float":
                self.params_table.w["v",name].set_limiter(rng)
            elif self._attributes[name].kind=="int":
                self.params_table.w["v",name].set_limiter(rng+("coerce","int"))
            elif self._attributes[name].kind=="enum":
                self.params_table.w["v",name].set_options(rng)
            self._attributes[name].rng[0]=rng
    

    def _show_attribute(self, name, show=True):
        for w in self._attributes[name].widgets:
            if w.objectName()=="dummy":
                p=w.sizePolicy()
                p.setRetainSizeWhenHidden(show)
                w.setSizePolicy(p)
            else:
                w.setVisible(show)
        self.params_table.set_visible("v/"+name,show)
    @exsafe
    def setup_visibility(self):
        """Update parameter rows visibility"""
        quick=self.buttons.v["quick_access"]
        for n in self._attributes:
            self._show_attribute(n,not quick or self.props_table.v["p_quick",n])
    

    def set_attribute_indicator(self, name, value):
        """Set attribute indicator value"""
        if name not in self._attributes:
            return
        if self._attributes[name].indicator:
            self.params_table.v["v",name]=value
        else:
            self.params_table.i["v",name]=value
            if name in self._sync_values:
                self.params_table.v["v",name]=value
                self._sync_values.remove(name)
    
    def set_error_indicator(self, name, value):
        """Set error indicator value"""
        if name not in self._attributes or self._attributes[name].indicator:
            return
        if value is None:
            self.params_table.v["e",name]=""
            self.params_table.w["e",name].setStyleSheet("")
            self.params_table.w["e",name].setToolTip("")
        else:
            self.params_table.v["e",name]="E"
            self.params_table.w["e",name].setStyleSheet("QLabel{background: red; color: white}")
            self.params_table.w["e",name].setToolTip(str(value))
    @exsafe
    def _clear_error_indicator(self, name):
        if name in self._attributes:
            self.cam_ctl.dev.ca.clear_camera_attributes_error(name)
    
    def update_attributes(self):
        """Update all attribute indicators"""
        self._activity_state="on" if self._activity_state=="updated" else self._activity_state
        active=self._activity_state=="on"
        self.tabs.setEnabled(active)
        self.buttons.set_enabled("quick_access",active)
        if self.cam_ctl.dev is not None:
            if active:
                parameters=self.cam_ctl.dev.v["parameters"]
                if "camera_attributes" in parameters:
                    for n,v in parameters["camera_attributes"].items(leafs=True,path_kind="joined"):
                        self.set_attribute_indicator(n,v)
                if "errors/camera_attributes" in parameters:
                    for n,v in parameters["errors/camera_attributes"].items(leafs=True,path_kind="joined"):
                        self.set_error_indicator(n,v)
                if "aux/camera_attributes_desc" in parameters:
                    for n,v in parameters["aux/camera_attributes_desc"].items(leafs=True,path_kind="joined"):
                        self._update_parameter_range(n,v)

    @exsafe
    def _set_camera_attributes(self, names):
        if not isinstance(names,(list,set)):
            names=[names]
        pause="none"
        for n in names:
            if self.props_table.v["p_pause",n]=="clear":
                pause="clear"
                break
            if self.props_table.v["p_pause",n]=="restart":
                pause="pause"
        self.cam_ctl.dev.ca.apply_parameters({"camera_attributes/"+n:self.params_table.v["v",n] for n in names},pause=pause)
    @exsafe
    def _on_change_attribute(self, name):
        if not self._autoset_paused and self.props_table.v["p_autoset",name]=="always":
            self._set_camera_attributes([name])
    
    def _setup_attributes_update(self, active):
        if self.cam_ctl.dev is not None:
            self.cam_ctl.dev.cai.modify_updated_camera_attributes(mode=active)
            if active:
                self.cam_ctl.dev.ca.update_parameters()
    @exsafe
    def activate(self, activate=True):
        """Activate or deactivate the window"""
        if activate and self._activity_state=="off":
            self._activity_state="activated"
            self._setup_attributes_update(True)
        elif not activate:
            self._activity_state="off"
            self._setup_attributes_update(False)
            self.update_attributes()
    def setup_startup(self):
        """Perform the connection setup: apply autoset parameters and set controls"""
        self._setup_connected_camera()
        to_set=set()
        for n in self._attributes:
            if not self._attributes[n].indicator:
                if self.props_table.v["p_autoset",n] in {"always","startup"}:
                    to_set.add(n)
                else:
                    self._sync_values.add(n)
        self._set_camera_attributes(to_set)
        if self._activity_state=="on":
            self._setup_attributes_update(True)

    def set_all_values(self, value):
        value=value or {}
        try:
            self._autoset_paused=True
            super().set_all_values(value)
            self._initial_values=self._initial_values or value.copy()
        finally:
            self._autoset_paused=False
    def get_all_values(self):
        values=super().get_all_values() if not self._error_raised else self._initial_values
        if "e" in values:
            del values["e"]
        return values