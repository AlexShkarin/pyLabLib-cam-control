from . import base
from pylablib.core.utils import dictionary, files as file_utils, string as string_utils
from pylablib.core.thread import controller
from pylablib.thread.stream import StreamSource, FramesMessage
from pylablib.devices.interface.camera import remove_status_line
from pylablib import widgets

import numpy as np
import os
import importlib
import sys


from .filters.base import IFrameFilter
from utils.gui import DisplaySettings_ctl, ProcessingIndicator_ctl




class FilterPanel(widgets.QFrameContainer):
    """
    Filter settings controller widget.

    Controls loading and enabling filters, manages their controls and default values storage.
    """
    def setup(self, plugin, filters, plotter=None):
        super().setup(no_margins=True)
        self.plugin=plugin
        self.current_filter=None
        self.plotter=plotter
        self.filter_captions=filters
        self.filter_defaults=dictionary.Dictionary()
        self.current_plotter=None
        self.plotter_parameters=None
        self.params=self.add_child("params",widgets.ParamTable(self))
        self.params.setup(add_indicator=False)
        self.params.add_combo_box("filter_id",label="Filter:",options=filters,out_of_range="ignore")
        self.params.add_button("load_filter","Load",location=(-1,2,1,1))
        self.params.w["load_filter"].setMinimumWidth(50)
        @controller.exsafe
        def load_filter():
            self.plugin.ca.load_filter(self.v["filter_id"])
        self.params.vs["load_filter"].connect(load_filter)
        @controller.exsafe
        def unload_filter():
            self.plugin.ca.unload_filter()
        self.params.add_button("unload_filter","Unload",location=("next",2,1,1))
        self.params.vs["unload_filter"].connect(unload_filter)
        self.params.add_text_label("loaded_filter",location=("next",0,1,"end"))
        self.params.add_text_label("filter_tab_label",location=("next",0,1,"end"))
        self.params.add_toggle_button("enabled","Enable",value=True,location=("next",0,1,"end"))
        self.params.add_text_label("description",location=("next",0,1,"end"))
        self.params.w["description"].setWordWrap(True)
        @controller.exsafe
        def enable_filter(enabled):
            self.plugin.ca.enable(enabled)
        self.params.vs["enabled"].connect(enable_filter)
        enable_filter(True)
        self.filter_params_table=self.add_child("filter_params",widgets.ParamTable(self),gui_values_path="current_filter_params")
        self.filter_params_table.setup(add_indicator=True)
        @controller.exsafe
        def apply_settings(name, value):
            self.plugin.ca.set_parameter(name,value)
        self.filter_params_table.contained_value_changed.connect(apply_settings)
        @controller.exsafe
        def on_lines_move():
            if self.params.v["enabled"]:
                self.plugin.ca.set_parameter("linepos",self.plotter.plt.get_line_positions())
        self.plotter.plt.lines_updated.connect(on_lines_move)
        self.add_spacer(20)
        self.filter_status_table=self.add_child("filter_status",widgets.ParamTable(self),gui_values_path="current_filter_status")
        self.filter_status_table.setup(add_indicator=True)
        self.add_padding("vertical")
        def set_filter_defaults(filter_defaults):
            self.filter_defaults=filter_defaults
        self.add_property_element("defaults",lambda: self.filter_defaults,set_filter_defaults)

    def start(self):
        self.load_default_values()
        super().start()
    @controller.call_in_gui_thread
    def setup_filter(self, name, description):
        """Setup filter panel given the description and load its default values"""
        self.store_default_values(exclude=["__plotter__"])
        self.current_filter=name,description
        self.params.v["loaded_filter"]=self.filter_captions.get(name,name)
        self.params.v["description"]=description.get("description","")
        for pdesc in description.get("gui/parameters",[]):
            pname=pdesc["name"]
            plabel=pdesc.get("label","name")
            pkind=pdesc.get("kind","float")
            pdefault=pdesc.get("default",None)
            plimit=pdesc.get("limit",(None,None))
            pfmt=pdesc.get("fmt",None)
            poptions=pdesc.get("options",{})
            pind=pdesc.get("indicator",False)
            if pkind=="text":
                if pind:
                    self.filter_status_table.add_text_label(pname,value=pdefault or "",label=plabel)
                else:
                    self.filter_params_table.add_text_edit(pname,value=pdefault or "",label=plabel)
            elif pkind in {"float","int"}:
                if pkind=="int" and pfmt is None:
                    pfmt="int"
                if pind:
                    self.filter_status_table.add_num_label(pname,value=pdefault or 0,formatter=pfmt,label=plabel)
                else:
                    self.filter_params_table.add_num_edit(pname,value=pdefault or 0,limiter=(plimit[0],plimit[1],"coerce",pkind),formatter=pfmt,label=plabel)
            elif pkind=="button":
                self.filter_params_table.add_button(pname,caption=plabel)
            elif pkind=="check":
                self.filter_params_table.add_check_box(pname,value=bool(pdefault),caption=plabel)
            elif pkind=="select":
                self.filter_params_table.add_combo_box(pname,value=pdefault,label=plabel,options=poptions,out_of_range="ignore")
            elif pkind=="virtual":
                if pind:
                    self.filter_status_table.add_virtual_element(pname,value=pdefault)
                else:
                    self.filter_params_table.add_virtual_element(pname,value=pdefault)
            else:
                raise ValueError("unrecognized parameter kind: {}".format(pkind))
        self.load_default_values(name,exclude=["__plotter__"])
    @controller.call_in_gui_thread
    def clear_filter(self):
        """Clear filter panel and store its default values"""
        if self.current_filter is not None:
            self.store_default_values(self.current_filter[0],exclude=["__plotter__"])
            self.filter_params_table.clear()
            self.filter_status_table.clear()
            self.params.v["description"]=""
            self.params.v["loaded_filter"]=""
            self.current_filter=None
            self.load_default_values(exclude=["__plotter__"])
    def update_indicators(self, values, data=None):
        """Update filter indicators and status values"""
        if not self.is_running():
            return
        image_updated=False
        if self.plotter is not None and data is not None:
            new_plotter=data.get("source",None)
            new_selector=data.get("plotter/selector",None)
            plotter_updated=new_plotter!=self.current_plotter or new_selector!=self.get_aux(self.current_plotter,"plotter_selector")
            if plotter_updated:
                self.store_default_values(self.current_plotter,include=["__plotter__"])
                self._store_plotter_selector(self.current_plotter)
                self.set_aux(new_plotter,"plotter_selector",new_selector)
                self._load_plotter_selector(new_plotter)
                self.load_default_values(new_plotter,include=["__plotter__"])
            new_rects=data.get("rectangles",{})
            current_rects=self.plotter.plt.get_rectangles()
            for n,p in new_rects.items():
                self.plotter.plt.set_rectangle(n,center=p.get("center",(0,0)),size=p.get("size",(0,0)),visible=p.get("visible",False))
            for n in set(current_rects)-set(new_rects):
                self.plotter.plt.del_rectangle(n)
            if "frame" in data:
                self.plotter.plt.set_image(data["frame"])
                image_updated=self.plotter.plt.update_image(do_redraw=plotter_updated)
            elif plotter_updated:
                self.plotter.plt.set_image([[np.nan]])
                self.plotter.plt.update_image(do_redraw=True)
            self.current_plotter=new_plotter
        self.filter_params_table.set_all_indicators(values)
        self.filter_status_table.set_all_values(values)
        if self.isVisible() and self.plotter is not None and not self.plotter.isVisible():
            self.params.v["filter_tab_label"]="Currently displaying a non-filter tab"
            self.params.w["filter_tab_label"].setStyleSheet("background: gold; color: black")
        else:
            self.params.v["filter_tab_label"]=""
            self.params.w["filter_tab_label"].setStyleSheet("")
        return image_updated
    def get_aux(self, name, path, default=None):
        """Get auxiliary data for the given filter name (if ``None``, return the default)"""
        if name is not None:
            return self.filter_defaults.get((name,"__aux__",path),default=default)
        return default
    def set_aux(self, name, path, value):
        """Set auxiliary data for the given filter name (if ``None``, do nothing)"""
        if name is not None or self.current_filter is not None:
            self.filter_defaults.add_entry((name,"__aux__",path),value,force=True)
    def _load_plotter_selector(self, plotter):
        selector=self.get_aux(plotter,"plotter_selector")
        selector_values=self.get_aux(plotter,("plotter",selector))
        if selector_values is not None:
            self.filter_defaults.add_entry((plotter,"__plotter__"),selector_values,force=True)
    def _store_plotter_selector(self, plotter):
        selector=self.get_aux(plotter,"plotter_selector")
        if selector is not None:
            self.set_aux(plotter,("plotter",selector),self.filter_defaults.get((plotter,"__plotter__"),{}))
    def get_all_values(self):
        if self.current_filter is not None:
            self.store_default_values(self.current_filter[0],exclude=["__plotter__"])
        self.store_default_values(self.current_plotter,include=["__plotter__"])
        self._store_plotter_selector(self.current_plotter)
        values=super().get_all_values()
        values["loaded"]=self.current_filter is not None
        if "current_filter_params" in values:
            del values["current_filter_params"]
        return values
    def set_all_values(self, values):
        super().set_all_values(values)
        if "defaults" in values:
            self.load_default_values(self.current_filter[0] if self.current_filter else None,exclude=["__plotter__"])
            self.load_default_values(self.current_plotter,include=["__plotter__"])
        if "loaded" in values:
            if values["loaded"]:
                self.v["load_filter"]=True
            else:
                self.v["unload_filter"]=True
    def get_filter_parameters(self):
        """Get filter parameters, including plotter settings"""
        values=self.filter_params_table.get_all_values()
        if self.plotter is not None:
            plot_values=self.plotter.get_all_values()
            values["__plotter__"]=plot_values
        return values.copy()
    def _set_plotter_parameters(self, values):
        if self.plotter and values:
            self.plotter.set_all_values(values)
            if not values.get("update_image",True):
                self.plotter.plt.arm_single()
    def set_filter_parameters(self, values):
        """Set filter parameters, including plotter settings"""
        if "__plotter__" in values:
            self._set_plotter_parameters(values.detach("__plotter__"))
        self.filter_params_table.set_all_values(values)
        self.filter_status_table.set_all_values(values)
    def load_default_values(self, name=None, include=None, exclude=None):
        """
        Load filter parameters from the list of stored values.
        
        `name` specifies the filter name (``None`` means the state with the filter disabled).
        `include` and `exclude` halp specify particular branches to load.
        """
        name=name or "__no_filter__"
        values=self.filter_defaults.get(name,dictionary.Dictionary()).copy()
        if exclude is not None:
            for k in exclude:
                if k in values:
                    del values[k]
        values.del_entry("__aux__")
        if include is not None:
            values=values.collect(include)
        self.set_filter_parameters(values)
    def store_default_values(self, name=None, include=None, exclude=None):
        """
        Save filter parameters to the list of stored values.
        
        `name` specifies the filter name (``None`` means the state with the filter disabled).
        `include` and `exclude` halp specify particular branches to store.
        """
        name=name or "__no_filter__"
        values=self.get_filter_parameters()
        exclude=(list(exclude) if exclude else [])+["__aux__"]
        for k in exclude:
            values.add_entry(k,self.filter_defaults.get(name,{}).get(k,{}),force=True)
        if include is None:
            self.filter_defaults.add_entry(name,values,force=True)
        else:
            include=[dictionary.normalize_path(k) for k in include]
            for k in include:
                self.filter_defaults.add_entry([name]+k,values.get(k,{}),force=True)








class FilterThread(controller.QTaskThread):
    """
    Filter thread controller.

    Feeds frames to the filter class and re-transmits the processed data.

    Setup args:
        - ``"src"``: frames message source
        - ``"tag"``: frames message tag
        - ``"settings"``: additional settings dictionary

    Variables:
        - ``"filter_desc"``: description of the currently loaded filter
        - ``"filter_parameters"``: current status and parameter values of the filter
    
    Commands:
        - ``set_filter``: set the filter class
        - ``remove_filter``: remove the filter class
        - ``get_new_data``: request new data from the filter
        - ``enable``: enable or disable filter processing
        - ``set_parameter``: set filter parameters
    """
    def setup_task(self, src, tag="frames/new", tag_out=None, settings=None):
        super().setup_task()
        self.frames_src=StreamSource(FramesMessage,sn=self.name)
        self.enabled=False
        self.fctl=None
        self._filter_received=False
        self._last_frame=None
        self._last_frame_index=None
        self._new_frames_received=True
        self.settings=settings or {}
        self.status_line_policy=self.settings.get("status_line_policy","duplicate")
        if self.status_line_policy not in {"keep","cut","zero","median","duplicate"}:
            self.status_line_policy="duplicate"
        self.subscribe_commsync(self.receive_message,srcs=src,tags=tag,limit_queue=20,priority=-5)
        self.tag_out=tag_out or tag+"/show"
        self.add_command("set_filter")
        self.add_command("remove_filter")
        self.add_command("prime_filter")
        self.add_command("get_new_data",priority=-5)
        self.add_command("enable")
        self.add_command("set_parameter")
        self.add_job("update_parameters",self.update_parameters,0.5,priority=0)
    def finalize_task(self):
        self.remove_filter()
        return super().finalize_task()

    def set_filter(self, fctl):
        """Set a new filter class"""
        self.remove_filter()
        self.fctl=fctl
        self.fctl.setup()
        for p in fctl.description.get("gui/parameters",[]):
            if ("name" in p) and ("default" in p) and (not p.get("indicator",True)) and p["default"] is not None:
                self.fctl.set_parameter(p["name"],p["default"])
        self.v["filter_props/parameters"]={p["name"]:p for p in fctl.description.get("gui/parameters",[]) if "name" in p}
        self.v["filter_desc"]=fctl.description
        self.single_frame=not fctl.description.get("receive_all_frames",False)
    def remove_filter(self):
        """Remove the filter class"""
        if self.fctl is not None:
            self.fctl.cleanup()
            self.fctl=None
            self.v["filter_props"]=None
            self._filter_received=False
            self.v["filter_desc"]={}
    
    def receive_message(self, src, tag, msg):
        self._new_frames_received=True
        if self.enabled and self.fctl is not None:
            self.frames_src.receive_message(msg)
            if self.single_frame:
                self._receive_frames(msg.last_frame(),msg.metainfo.get("status_line"),single=True,chandim=msg.mi.chandim)
            else:
                self._receive_frames(msg.frames,msg.metainfo.get("status_line"),single=False,chandim=msg.mi.chandim)
        self._last_frame=remove_status_line(msg.last_frame(),msg.metainfo.get("status_line"),policy=self.status_line_policy,copy=True)
        self._last_frame_index=msg.last_frame_index()
    def _receive_frames(self, frames, status_line, single=False, chandim=0):
        if single:
            frames=frames[None,:,:].copy()
        else:
            frames=np.array(frames) if frames and frames[0].ndim==2+chandim else np.concatenate(frames,axis=0)
        frames=remove_status_line(frames,status_line,policy=self.status_line_policy,copy=False)
        self.fctl.receive_frames(frames)
        self._filter_received=True

    def prime_filter(self):
        """Feed the latest received frame to a newly loaded filter"""
        if self.fctl is not None and self._last_frame is not None and not self._filter_received:
            self.fctl.receive_frames(self._last_frame[None,:,:])
            self._filter_received=True
    def get_new_data(self, only_new=True):
        """Request new data from the filter"""
        if not self._new_frames_received and only_new:
            return None,None
        self._new_frames_received=False
        if self.enabled and self.fctl is not None:
            data=self.fctl.generate_data()
        else:
            data={"frame":self._last_frame} if self._last_frame is not None else {}
        data["source"]=self.fctl.get_class_name() if (self.enabled and self.fctl is not None) else None
        if "frame" in data:
            self.send_multicast(dst="any",tag=self.tag_out,value=self.frames_src.build_message(data["frame"],self._last_frame_index,source=self.name))
        return data,self.update_parameters()
    def update_parameters(self):
        """Update filter parameters and status"""
        if self.fctl is not None:
            self.v["filter_parameters"]=self.fctl.get_all_parameters()
            return self.v["filter_parameters"]
        else:
            self.v["filter_parameters"]={}
            return {}
    def enable(self, enabled=True):
        """Enable or disable the filter"""
        self.enabled=enabled
    def set_parameter(self, name, value):
        """The the filter parameter"""
        if self.fctl is not None and name in self.get_variable("filter_props/parameters",default=[]):
            self.fctl.set_parameter(name,value)






class FilterPlugin(base.IPlugin):
    _class_name="filter"
    def setup(self):
        self._collect_filters()
        self.caption=self.parameters.get("caption","Filter")
        self.filter=None
        self.filter_enabled=False
        self.filter_thread=FilterThread(self.ctl.name+".filter_thread",kwargs={"src":self.extctls["slowdown"].name,"settings":self.parameters})
        self.filter_thread.start()
        self.filter_thread.sync_exec_point("run")
        self.ctl.add_command("load_filter",self.load_filter)
        self.ctl.add_command("unload_filter",self.unload_filter)
        self.ctl.add_command("enable",self.enable)
        self.ctl.add_command("set_parameter",self.set_parameter)
        self.ctl.add_command("get_all_parameters",self.get_all_parameters)
        self.ctl.add_command("update_plots",self.update_plots)
        self.setup_gui_sync()
        self.extctls["resource_manager"].cs.add_resource("frame/display",self.full_name,ctl=self.ctl,
            caption=self.caption,src=self.filter_thread.name,tag=self.filter_thread.tag_out,frame=None)
        self.extctls["resource_manager"].cs.add_resource("process_activity","processing/"+self.full_name,ctl=self.ctl,
            caption=self.caption,order=10)
        self.ctl.add_job("update_plots",self.update_plots,0.1)
        self.ctl.add_job("update_indicators",self.update_indicators,0.1,priority=-15)
    def setup_gui(self):
        self.plot_tab=self.gui.add_plot_tab("plt_tab",self.caption,kind="empty")
        self.proc_indicator=self.plot_tab.add_child("processing_indicator",ProcessingIndicator_ctl.ProcessingIndicator_GUI(self.plot_tab),gui_values_path="procind")
        self.proc_indicator.setup([
                ("binning",ProcessingIndicator_ctl.binning_item(self.extctls["preprocessor"].name)),
                ("filter",("Filter",self._get_filter_state))],update=False)
        self.plotter=self.plot_tab.add_to_layout(widgets.ImagePlotterCombined(self.plot_tab))
        self.plotter.setup(name="image_plotter",ctl_caption="Image settings")
        self.plotter.w["minlim"].set_formatter(".02f")
        self.plotter.w["maxlim"].set_formatter(".02f")
        self.plotter.v["normalize"]=True
        with self.plotter.using_layout("sidebar"):
            self.display_settings_table=DisplaySettings_ctl.DisplaySettings_GUI(self.plotter)
            self.plotter.add_child("display_settings_table",self.display_settings_table,gui_values_path="disp",location=-1)
            self.display_settings_table.setup(slowdown_thread=self.extctls["slowdown"].name,period_update_tag=None)
            self.display_settings_table.params.vs["display_update_period"].connect(lambda v: self.ctl.ca.change_job_period("update_plots",v))
        self.plotter.plt.set_colormap("hot_sat")
        self.filter_panel=self.gui.add_control_tab("ctl_tab",self.caption,kind=FilterPanel)
        self.filter_panel.setup(self,self.filter_captions,plotter=self.plotter)
        self.proc_indicator.update_indicators()
        self.gui.control_tabs.currentChanged.connect(self._check_tab)
    @controller.exsafe
    def _check_tab(self, index):
        if self.gui.is_running() and index==self.gui.control_tabs.indexOf(self.filter_panel):
            self.gui.plot_tabs.setCurrentIndex(self.gui.plot_tabs.indexOf(self.plot_tab))
    def cleanup(self):
        self.unload_filter()
        return super().cleanup()
    def set_all_values(self, values):
        if values.get("ctl_tab/enabled",False) and values.get("ctl_tab/loaded",False) and not self._gui_started:
            values["ctl_tab/enabled"]=False
        super().set_all_values(values)
        self.proc_indicator.update_indicators()

    @controller.call_in_gui_thread
    def _update_image(self, values=None, data=None):
        if values is not None and self.filter_panel.update_indicators(values=values,data=data):
            self.proc_indicator.update_indicators()
            self.display_settings_table.on_new_frame()
            return True
        return False
    def _get_filter_state(self):
        current_filter=self.filter_panel.current_filter
        if current_filter is not None and self.filter_panel.v["enabled"]:
            return current_filter[1]["caption"]
        return None
    def update_indicators(self):
        self._update_image(values=self.filter_thread.get_variable("filter_parameters",None))
    def update_plots(self, force=False):
        """Update plots"""
        if force:
            self.filter_thread.cs.prime_filter()
        data,values=self.filter_thread.cs.get_new_data(only_new=not force)
        if self._update_image(values=values,data=data):
            self.extctls["resource_manager"].csi.update_resource("frame/display",self.full_name,frame=data["frame"])

    def _collect_filters(self):
        fcls=find_filters(os.path.join("plugins","filters"),root=self.gui.settings["runtime/root_folder"])
        self.filter_classes={cls.get_class_name():cls for cls in fcls}
        self.filter_captions={cls.get_class_name():cls.get_class_name(kind="caption") for cls in fcls}

    def load_filter(self, name):
        """Load filter with the given name"""
        self.unload_filter(update=False)
        self.filter=self.filter_classes[name]()
        self.filter_thread.cs.set_filter(self.filter)
        self.filter_panel.setup_filter(name,self.filter_thread.v["filter_desc"])
        self.update_filter_state()
        self.ca.update_plots(force=True)
    def unload_filter(self, update=True):
        """Unload the currently loaded filter"""
        if self.filter is not None:
            self.filter_thread.csi.remove_filter()
            self.filter_panel.clear_filter()
            self.filter=None
            if update:
                self.update_filter_state()
                self.ca.update_plots(force=True)

    def update_filter_state(self):
        enabled=(self.filter is not None) and self.filter_enabled
        self.extctls["resource_manager"].csi.update_resource("process_activity","processing/"+self.full_name,status="on" if enabled else "off")
    def enable(self, enabled=True):
        """Enable or disable the filter"""
        self.filter_enabled=enabled
        self.update_filter_state()
        self.filter_thread.cs.enable(enabled=enabled)
        self.update_plots(force=True)
    def set_parameter(self, name, value):
        """Set the filter parameter"""
        return self.filter_thread.cs.set_parameter(name,value)
    def get_all_parameters(self):
        """Get all current filter parameter"""
        return self.filter_thread.get_variable("filter_parameters",dictionary.Dictionary()).asdict("flat")


def find_filters(folder, root=""):
    """
    Find all filter classes in all files contained in the given folder.

    Filter class is any subclass of :cls:`IFrameFilter` which has ``_class_name`` attribute which is not ``None``.
    """
    files=file_utils.list_dir_recursive(os.path.join(root,folder),file_filter=r".*\.py$",visit_folder_filter=string_utils.get_string_filter(exclude="__pycache__")).files
    filters=[]
    for f in files:
        f=os.path.join(folder,f)
        module_name=os.path.splitext(f)[0].replace("\\",".").replace("/",".")
        if module_name not in sys.modules:
            spec=importlib.util.spec_from_file_location(module_name,os.path.join(root,f))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules[module_name]=mod
        mod=sys.modules[module_name]
        for v in mod.__dict__.values():
            if isinstance(v,type):
                if issubclass(v,IFrameFilter) and getattr(v,"_class_name") is not None:
                    filters.append(v)
    return filters