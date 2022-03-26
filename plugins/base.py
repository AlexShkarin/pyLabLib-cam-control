from pylablib.core.thread import controller
from pylablib.core.utils import files as file_utils, string as string_utils
from pylablib.core.gui.widgets import container
from pylablib.core.gui import QtWidgets, utils
from pylablib import widgets

import importlib
import os
import sys


class PluginThreadController(controller.QTaskThread):
    """
    Plugin thread controller.

    Takes care of setting up and tearing down the plugin
    and provides it with means to set up jobs, commands, multicast subscriptions, etc.

    Setup args:
        - ``name``: plugin name
        - ``plugin_cls``: plugin controller class (subclass of :cls:`IPlugin`)
        - ``main_frame``: main GUI :cls:`.QFrame` object
        - ``parameters``: additional parameters passed to the plugin on creation
        - ``ext_controller_names``: dictionary with aliases and real names of additional controllers (camera, saver, etc)
    """
    def setup_task(self, name, plugin_cls, main_frame, notifier=None, parameters=None, ext_controller_names=None):
        self.plugin=None
        self.main_frame=main_frame
        ext_controllers={a:controller.sync_controller(n) for a,n in ext_controller_names.items()} if ext_controller_names else None
        gui_ctl=self._make_manager(main_frame,"{}.{}".format(plugin_cls.get_class_name(),name))
        self.plugin=plugin_cls(name,self,gui_ctl,parameters=parameters,ext_controllers=ext_controllers)
        self.plugin._open()
        self.notify_exec_point("plugin_setup")
        if notifier is not None:
            notifier.wait()
        self.main_frame.initialize_plugin(self.plugin)  # GUI values are set here

    @controller.call_in_gui_thread
    def _make_manager(self, main_frame, full_name):
        manager=PluginGUIManager(main_frame)
        manager.setup(main_frame,name_prefix=full_name+"/")
        return manager

    @controller.call_in_gui_thread
    def get_all_values(self): # called in GUI thread to avoid potential deadlocks
        """Get all plugin GUI values"""
        return self.plugin.get_all_values()
    @controller.call_in_gui_thread
    def set_all_values(self, values):
        """Set all plugin GUI values; executed in GUI thread"""
        return self.plugin.set_all_values(values)
    def get_all_indicators(self):
        """Get all plugin GUI indicators; executed in GUI thread"""
        return self.plugin.get_all_indicators()
    def is_plugin_setup(self):
        """Check if the plugin has been set up"""
        return bool(self.get_exec_counter("plugin_setup"))
    def is_plugin_running(self):
        """Check if the plugin is running"""
        return bool(self.get_exec_counter("run"))

    def finalize_task(self):
        if self.plugin is not None:
            self.main_frame.finalize_plugin(self.plugin)
            self.plugin._close()



class PluginGUIManager(container.QContainer):
    """
    A collection of all GUI-managing objects accessible to a plugin thread
    
    Args:
        main_frame: main GUI :cls:`.QFrame` object
    """
    def setup(self, main_frame, name_prefix=""):
        self.main_frame=main_frame
        self.settings=main_frame.settings
        self.all_gui_values=main_frame.gui_values
        self.plot_tabs=main_frame.plots_tabs
        self.control_tabs=main_frame.control_tabs
        self.plugin_tab=main_frame.control_tabs.c["plugins"]
        self.name_prefix=name_prefix
        self._container_boxes={}
        self.main_frame.add_child(self.name_prefix+"__controller__",self,gui_values_path="plugins/"+self.name_prefix)
    def start(self): 
        if self._running:
            return
        self._running=True
        # starting of sub-widgets is done through their normal GUI parents
        for n in self._timers:
            self.start_timer(n)
    def stop(self): 
        if not self._running:
            return
        self._running=False
        # stopping of sub-widgets is done through their normal GUI parents
        for n in self._timers:
            self.stop_timer(n)

    def remove_child(self, name):
        name=self._normalize_name(name)
        super().remove_child(name)
        gui_name=self.name_prefix+name
        if gui_name in self.control_tabs.c:
            self.control_tabs.remove_tab(gui_name)
        if gui_name in self.plot_tabs.c:
            self.plot_tabs.remove_tab(gui_name)
        if gui_name in self._container_boxes:
            box=self._container_boxes.pop(gui_name)
            self.plugin_tab.remove_layout_element(box)
    def _add_tab(self, dst, name, caption, kind="empty", index=None, layout="vbox", **kwargs):
        if isinstance(kind,QtWidgets.QWidget):
            widget=kind
        elif isinstance(kind,type) and issubclass(kind,QtWidgets.QWidget):
            widget=kind(self.main_frame)
        elif kind=="params":
            widget=widgets.ParamTable(self.main_frame)
            kwargs.setdefault("gui_thread_safe",True)
            kwargs.setdefault("cache_values",True)
        elif kind=="line_plot":
            widget=widgets.LinePlotter(self.main_frame)
        elif kind=="trace_plot":
            widget=widgets.TracePlotterCombined(self.main_frame)
        elif kind=="image_plot":
            widget=widgets.ImagePlotterCombined(self.main_frame)
        elif kind=="empty":
            widget=None
        else:
            raise ValueError("unrecognized tab kind: {}".format(kind))
        name=self._normalize_name(name)
        tab=dst.add_tab(self.name_prefix+name,caption,widget=widget,index=index,layout=layout,gui_values_path=False)
        self.add_child(name,tab,gui_values_path=name)
        if kind in ["params","line_plot","trace_plot","image_plot"]:
            tab.setup(**kwargs)
        return tab
    def _add_box(self, dst, name, caption, kind="empty", layout="vbox", index=None, **kwargs):
        if isinstance(kind,QtWidgets.QWidget):
            widget=kind
        elif isinstance(kind,type) and issubclass(kind,QtWidgets.QWidget):
            widget=kind(self.main_frame)
        elif kind=="params":
            widget=widgets.ParamTable(self.main_frame)
            kwargs.setdefault("gui_thread_safe",True)
            kwargs.setdefault("cache_values",True)
        elif kind=="empty":
            widget=None
        else:
            raise ValueError("unrecognized tab kind: {}".format(kind))
        name=self._normalize_name(name)
        if dst.get_sublayout_kind()=="grid":
            if index is None:
                index=utils.get_first_empty_row(dst.get_sublayout())
            location=(index,0,1,"end")
        else:
            location=(-1,0) if index is None else (index,0)
        box=dst.add_group_box(self.name_prefix+name,caption,layout=layout,location=location,gui_values_path=False)
        if widget is None:
            widget=box
        else:
            box.add_child("c",widget,gui_values_path=False)
        self._container_boxes[self.name_prefix+name]=box
        self.add_child(name,widget,gui_values_path=name)
        if kind=="params":
            widget.setup(**kwargs)
        return widget
    def add_control_tab(self, name, caption, kind="params", index=None, layout="vbox", **kwargs):
        """
        Add a new tab to the control (right) tab group.

        Args:
            name: tab object name
            caption: tab caption
            kind: tab kind; can be ``"empty"`` (a simple empty :class:`.QFrameContainer` panel), ``"params"`` (:class:`.ParamTable` panel),
                an already created widget, or a widget class (which is instantiated upon addition)
            index: index of the new tab; add to the end by default
            layout: if `kind` is ``"empty"``, specifies the layout of the new tab
            kwargs: keyword arguments passed to the widget ``setup`` method when ``kind=="params"``
        """
        return self._add_tab(self.control_tabs,name,caption,kind=kind,index=index,layout=layout,**kwargs)
    def add_plot_tab(self, name, caption, kind="image_plot", index=None, layout="vbox", **kwargs):
        """
        Add a new tab to the plot (left) tab group.

        Args:
            name: tab object name
            caption: tab caption
            kind: tab kind; can be ``"empty"`` (a simple empty :class:`.QFrameContainer` panel), ``"params"`` (:class:`.ParamTable` panel),
                ``"line_plot"`` (a simple :class:`.LinePlotter` plotter), ``"trace_plot"`` (a more advanced :class:`.TracePlotterCombined` plotter),
                ``"image_plot"`` (a standard :class:`.ImagePlotterCombined` plotter),
                an already created widget, or a widget class (which is instantiated upon addition)
            index: index of the new tab; add to the end by default
            layout: if `kind` is ``"empty"``, specifies the layout of the new tab
            kwargs: keyword arguments passed to the widget ``setup`` method when the new tab is a parameter table or a plotter
        """
        return self._add_tab(self.plot_tabs,name,caption,kind=kind,index=index,layout=layout,**kwargs)
    def add_plugin_box(self, name, caption, kind="params", layout="vbox", index=None, **kwargs):
        """
        Add a new box to the plugins tab.

        Args:
            name: box object name
            caption: box caption
            kind: tab kind; can be ``"empty"`` (a simple empty :class:`.QFrameContainer` panel), ``"params"`` (:class:`.ParamTable` panel),
                an already created widget, or a widget class (which is instantiated upon addition)
            layout: if `kind` is ``"empty"``, specifies the layout of the new tab
            kwargs: keyword arguments passed to the widget ``setup`` method when ``kind=="params"``
        """
        return self._add_box(self.plugin_tab,name,caption,kind=kind,layout=layout,index=index,**kwargs)



class IPlugin:
    """
    A base class for a plugin.

    Provides some supporting code, basic implementation of some methods, and some helpful methods.

    Attributes which can be used in implementation:
        ctl: plugin thread controller (instance of :cls:`PluginThreadController`);
            used for threading activity such as setting up jobs, commands, subscribing to signals, etc.
        guictl: main (GUI) thread controller;
            used mainly for calling predefined thread methods (which access widgets, and therefore automatically execute in GUI thread)
        gui: GUI controller (instance of :cls:`PluginGUIManager`);
            used to set up GUI controls, e.g., add plotting or control tabs, or control boxes for small plugins
        extctls: dictionary of controller for additional thread;
            used to further access different parts of the system;
            threads include ``"camera"`` (camera thread), ``"saver"`` (main saver thread), ``"snap_saver"`` (snapshot saver thread),
            ``"processor"`` (default frame processing thread), ``'preprocessor"`` (frame preprocessor thread), ``"plot_accumulator`` (main plot accumulator thread)

    Args:
        name: plugin instance name
        ctl: plugin thread controller (instance of :cls:`PluginThreadController`)
        gui: plugin GUI manager
        parameters: additional parameters supplied in the settings file (``None`` of no parameters)
        ext_controllers: dictionary with external controllers (such as camera or saver)
    """
    def __init__(self, name, ctl, gui, parameters=None, ext_controllers=None):
        self.name=name
        self.full_name="{}.{}".format(self.get_class_name(),self.name)
        self.ctl=ctl
        self.ca=self.ctl.ca
        self.cs=self.ctl.cs
        self.csi=self.ctl.csi
        self.guictl=controller.get_gui_controller()
        self.extctls=ext_controllers or {}
        self.parameters=parameters or {}
        self.gui=gui
        self._running=False
        self._gui_started=False

    _class_name=None  # default class name (by default, the class name)
    _class_caption=None  # default class caption (by default, same as name)
    _default_start_order=0  # default starting order for plugins of this class
    @classmethod
    def get_class_name(cls, kind="name"):
        """
        Get plugin class name.

        `kind` can be ``"name"`` (code-friendly identifiers to use in, e.g., settings file)
        or ``"caption"`` (formatted name to be used in GUI lists, etc.)
        """
        if kind=="name":
            if cls._class_name is not None:
                return cls._class_name
            return cls.__name__
        elif kind=="caption":
            if cls._class_caption is not None:
                return cls._class_caption
            return cls.get_class_name(kind="name")
    def get_instance_name(self, kind="name"):
        """Get plugin instance name"""
        if kind=="name":
            return self.name
    
    def setup(self):
        """
        Setup plugin (define attributes, jobs, etc).

        To be overloaded.
        Executed in the plugin thread.
        """

    def cleanup(self):
        """
        Cleanup plugin (close handlers, etc).

        To be overloaded.
        Executed in the plugin thread.
        """

    def _open(self):
        self.setup()
        self._running=True
    def _close(self):
        self._running=False
        self.cleanup()
        controller.call_in_gui_thread(self.gui.clear)()
    def is_running(self):
        """Check if the plugin is still running"""
        return self._running

    @controller.exsafe
    def exit(self):
        """Stop the plugin thread and close the plugin"""
        self.ctl.stop()

    @controller.call_in_gui_thread
    def setup_gui_sync(self):
        """Setup GUI (simply calls :meth:`setup_gui` in the GUI thread)"""
        self.setup_gui()
    def setup_gui(self):
        """
        Setup GUI.

        To be overloaded.
        Executed in the plugin thread, if called via :meth:`setup_gui_sync` method.
        """

    def get_all_values(self):
        """
        Get all GUI values.

        Can be overloaded.
        Executed in the GUI thread.
        """
        return self.gui.get_all_values()
    def set_all_values(self, values):
        """
        Set all GUI values.

        Can be overloaded.
        Executed in the GUI thread.
        """
        self.gui.set_all_values(values)
    def get_all_indicators(self):
        """
        Get all GUI indicators as a dictionary.

        Can be overloaded.
        Executed in the GUI thread.
        """
        return self.gui.get_all_indicators()
    def start_gui(self):
        """
        Start GUI operation.

        Called after all GUI values are set.
        Can be overloaded.
        Executed in the GUI thread.
        """
        self._gui_started=True




def find_plugins(folder, root=""):
    """
    Find all plugin classes in all files contained in the given folder.

    Plugin class is any subclass of :cls:`IPlugin` which is not :cls:`IPlugin` itself.
    """
    files=file_utils.list_dir_recursive(os.path.join(root,folder),file_filter=r".*\.py",visit_folder_filter=string_utils.get_string_filter(exclude="__pycache__")).files
    plugins=[]
    for f in files:
        f=os.path.join(folder,f)
        module_name=f[:-3].replace("\\",".")
        if module_name not in sys.modules:
            spec=importlib.util.spec_from_file_location(module_name,os.path.join(root,f))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules[module_name]=mod
        mod=sys.modules[module_name]
        for v in mod.__dict__.values():
            if isinstance(v,type) and issubclass(v,IPlugin) and v is not IPlugin:
                plugins.append(v)
    return plugins