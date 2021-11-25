# Copyright (C) 2021  Alexey Shkarin

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
if __name__=="__main__":
    startdir=os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
    sys.path.append(os.path.abspath("."))  # set current folder to the file location and add it to the search path

from pylablib.core.thread import controller, synchronizing
from pylablib.core.gui.widgets import container, param_table
from pylablib.core.fileio import loadfile, savefile
from pylablib.core.utils import dictionary, general as general_utils
from pylablib import widgets as pll_widgets
import pylablib

from pylablib.core.gui import QtWidgets, QtCore, Signal
import pyqtgraph
pyqtgraph.setConfigOptions(useOpenGL=True,antialias=False)

import argparse
import datetime
import collections
import threading

from utils.gui import camera_control, SaveBox_ctl, GenericCamera_ctl, ProcessingIndicator_ctl, ActivityIndicator_ctl
from utils.gui import DisplaySettings_ctl, FramePreprocess_ctl, FrameProcess_ctl, PlotControl_ctl
from utils.gui import tutorial, color_theme
from utils import services, devthread
import plugins


### Redirecting console / errors to file logs ###
log_lock=threading.Lock()
class StreamLogger(general_utils.StreamFileLogger):
    def __init__(self, path, stream=None):
        general_utils.StreamFileLogger.__init__(self,path,stream=stream,lock=log_lock)
        self.start_time=datetime.datetime.now()
    def write_header(self, f):
        f.write("\n\n"+"-"*50)
        f.write("\nStarting {} {:on %Y/%m/%d at %H:%M:%S}\n\n".format(os.path.split(sys.argv[0])[1],self.start_time))
sys.stderr=StreamLogger("logerr.txt",sys.stderr)
sys.stdout=StreamLogger("logout.txt",sys.stdout)



version="2.1.0"
_defaults_filename="defaults.cfg"

cam_thread="camera"
process_thread="frame_process"
preprocess_thread="frame_preprocess"
slowdown_thread="frame_slowdown"
channel_accumulator_thread="channel_accumulator"
save_thread="frame_save"
snap_save_thread="frame_save_snap"
settings_manager_thread="settings_manager"
resource_manager_thread="resource_manager"


### Main window ###
class StandaloneFrame(container.QWidgetContainer):
    @controller.exsafe
    def setup(self, settings, cam_name):
        super().setup(layout="hbox")
        self.ctl.res_mgr=controller.sync_controller(resource_manager_thread)
        
        self.cam_kind=camera_kinds[settings["cameras",cam_name,"kind"]]
        self.cam_name=cam_name
        self.settings=settings
        self.gui_level="full"
        self.compact_interface=settings.get("interface/compact",False)

        ### Setup GUI
        cam_display_name=settings["cameras",self.cam_name].get("display_name",self.cam_name)
        self.setWindowTitle("{} control".format(cam_display_name))
        self.cam_ctl=camera_control.GenericCameraCtl(
            cam_thread=cam_thread,frame_src_thread=process_thread,preprocess_thread=preprocess_thread,
            save_thread=save_thread,snap_save_thread=snap_save_thread,resource_manager_thread=resource_manager_thread,
            frame_tag="frames/new/show",cam_name=cam_name,settings=settings)
        self.add_child("cam_controller",self.cam_ctl,gui_values_path="cam")
        self.cam_ctl.setup()
        # Setup plots
        with self.using_new_sublayout("plots","vbox"):
            self.plots_tabs=self.add_child("plot_tabs",container.QTabContainer(self))
            self.plots_tabs.setup()
            self.trace_plotter=self.add_to_layout(pyqtgraph.PlotWidget(self))
            self.trace_plotter.setMinimumSize(400,200)
            self.set_row_stretch(0,1)
            image_tab=self.plots_tabs.add_tab("standard_frame","Standard",layout="vbox")
            self.image_proc_indicator=image_tab.add_child("processing_indicator",ProcessingIndicator_ctl.ProcessingIndicator_GUI(self),gui_values_path="procind")
            self.image_proc_indicator.setup([
                    ("binning",ProcessingIndicator_ctl.binning_item(preprocess_thread)),
                    ("background",ProcessingIndicator_ctl.background_item(process_thread))])
            self.cam_ctl.image_updated.connect(self.image_proc_indicator.update_indicators)
            self.image_plotter=image_tab.add_to_layout(pll_widgets.ImagePlotterCombined(self))
            self.image_plotter.setup(name="image_plotter",min_size=(400,400),ctl_caption="Image settings")
            self.cam_ctl.add_child("plotter_area",self.image_plotter.plt,gui_values_path=False)
            self.cam_ctl.add_child("plotter_ctl",self.image_plotter.ctl,gui_values_path="img")
            self.image_plotter.ctl.set_img_lim(-65536,65536)
            with self.image_plotter.using_layout("sidebar"):
                self.display_settings_table=DisplaySettings_ctl.DisplaySettings_GUI(self)
                self.image_plotter.add_to_layout(self.display_settings_table,location=-1)
                self.add_child("display_settings_table",self.display_settings_table,gui_values_path="disp",location="skip")
                self.display_settings_table.setup(slowdown_thread=slowdown_thread)
                self.cam_ctl.image_updated.connect(self.display_settings_table.on_new_frame)
            self.image_plotter.plt.set_colormap("gray_sat")
        # Setup status and saving
        if not self.compact_interface:
            with self.using_new_sublayout("status_saving","vbox"):
                self._add_savebox(self)
                status_box=self.add_group_box("status_box",caption="Status")
                self._add_camstatus(status_box)
                self._add_savestatus(status_box)
                self.add_padding()
        # Setup control tab widget
        with self.using_new_sublayout("control_tabs_box","vbox"):
            self.control_tabs=self.add_child("control_tabs",container.QTabContainer(self))
            self.control_tabs.setMinimumWidth(300 if self.compact_interface else 270)
            self.control_tabs.setup()
            self._add_param_loading(self)
        cam_tab=self.control_tabs.add_tab("cam_tab","Camera",no_margins=False)
        self.cam_settings_table=self.cam_kind.controller(self)
        cam_tab.add_group_box("cam_settings_box",caption="Camera settings",no_margins=False).add_to_layout(self.cam_settings_table)
        self.cam_settings_table.setup(self.cam_ctl)
        self.cam_ctl.add_child("settings",self.cam_settings_table,gui_values_path="cam")
        if self.compact_interface:
            cam_tab.add_spacer(20)
            self._add_camstatus(cam_tab)
            cam_tab.add_padding(stretch=1)
            save_tab=self.control_tabs.add_tab("save_tab","Saving",no_margins=False)
            self._add_savebox(save_tab)
            save_tab.add_spacer(20)
            self._add_savestatus(save_tab)
            save_tab.add_padding(stretch=1)
        else:
            cam_tab.add_padding(stretch=1)
        proc_tab=self.control_tabs.add_tab("proc_tab","Processing",no_margins=False)
        self.frame_preprocessing_settings=proc_tab.add_child("frame_preprocessing",FramePreprocess_ctl.FramePreproccessBinning_GUI(self),gui_values_path="preproc/*")
        self.frame_preprocessing_settings.setup(preprocess_thread=preprocess_thread)
        self.slowdown_settings=proc_tab.add_child("slowdown",FramePreprocess_ctl.FramePreproccessSlowdown_GUI(self),gui_values_path="preproc/*")
        self.slowdown_settings.setup(slowdown_thread=slowdown_thread)
        self.frame_processing_settings=proc_tab.add_child("frame_processing",FrameProcess_ctl.FrameProccess_GUI(self),gui_values_path="proc")
        self.frame_processing_settings.setup(process_thread=process_thread,settings=settings.get("frame_processing"))
        proc_tab.add_spacer(10)
        self.plotting_settings=proc_tab.add_child("plotting_settings",PlotControl_ctl.PlotControl_GUI(self),gui_values_path="plotting")
        self.plotting_settings.setup(channel_accumulator_thread,self.trace_plotter,settings=settings)
        self.plotting_settings.set_all_values({"update_plot":True,"disp_last":1000,"roi/center/x":16,"roi/center/y":16,"roi/size/x":32,"roi/size/y":32})
        proc_tab.add_padding()
        self.control_tabs.setMaximumWidth(300)
        self.set_column_stretch(0,1)
        self.cam_ctl.set_all_values({"img/normalize":True})
        self.activity_indicator=self.add_child("activity_indicator",ActivityIndicator_ctl.ActivityIndicator_GUI(self))
        self.activity_indicator.setup(resource_manager_thread=resource_manager_thread)
        # add virtual GUI values
        self.add_property_element("defaults/window/size",
            lambda: (self.size().width(),self.size().height()), lambda v: self.resize(*v), add_indicator=False)
        self.add_property_element("defaults/window/position",
            lambda: (self.geometry().x(),self.geometry().y()), lambda v: self.setGeometry(v[0],v[1],self.size().width(),self.size().height()), add_indicator=False)
        self.add_property_element("defaults/window/maximized",
            lambda: self.windowState()==QtCore.Qt.WindowMaximized, lambda v: self.showMaximized() if v else None, add_indicator=False)
        self.add_virtual_element("defaults/settings_folder",value="",add_indicator=False)
        self.tutorial_box=None

        # Setup plugins
        plugin_tab=self.control_tabs.add_tab("plugins","Plugins",gui_values_path="plugins",layout="grid")
        plugin_tab.add_padding(stretch=1,location=50)
        self._loading_plugins={}
        self._running_plugins={}
        self._plugin_classes={p.get_class_name():p for p in plugins.find_plugins("plugins",root=settings["runtime/root_folder"])}
        self._plugin_parameters=dictionary.Dictionary()

        # Setup parameters loading and saving
        if "interface/level" in settings:
            self.set_gui_level(settings["interface/level"])
        # Setup settings manager
        settings_ctl=controller.sync_controller(settings_manager_thread)
        settings_ctl.ca.add_source("gui",controller.call_in_gui_thread(lambda: self.get_all_values(full_status=True)))
        settings_ctl.ca.update_settings("cfg",settings.copy())
        # Setup thread methods and signals
        self.ctl.finished.connect(self.stop)
        self.ctl.add_thread_method("get_all_values",self.get_all_values)
        self.ctl.add_thread_method("set_all_values",self.set_all_values)
        # Load plugins
        self.load_config_plugins()

    def _add_savebox(self, parent):
        self.saving_settings_table=parent.add_to_layout(SaveBox_ctl.SaveBox_GUI(self))
        self.saving_settings_table.setup(self.cam_ctl)
        self.cam_ctl.add_child("savebox",self.saving_settings_table,gui_values_path="save")
    def _add_camstatus(self, parent):
        self.cam_status_table=parent.add_to_layout(self.cam_kind.status(self))
        self.cam_status_table.setup(self.cam_ctl)
        self.cam_ctl.add_child("camstat",self.cam_status_table,gui_values_path="camstat")
    def _add_savestatus(self, parent):
        self.save_status_table=parent.add_to_layout(SaveBox_ctl.SaveStatus_GUI(self))
        self.save_status_table.setup(self.cam_ctl)
        self.cam_ctl.add_child("savestat",self.save_status_table,gui_values_path="savestat")
    def _add_param_loading(self, parent):
        self.params_loading_settings=parent.add_to_layout(param_table.ParamTable(self))
        self.add_child("params_loading_settings",self.params_loading_settings,location="skip")
        self.params_loading_settings.setup(add_indicator=False)
        with self.params_loading_settings.using_new_sublayout("buttons","hbox"):
            self.params_loading_settings.add_button("load_settings","Load settings...")
            self.params_loading_settings.add_button("save_settings","Save settings...")
        with self.params_loading_settings.using_new_sublayout("scope","hbox"):
            self.params_loading_settings.add_combo_box("settings_load_scope",label="Loading scope:",options=["All","Camera","GUI"],index_values=["all","camera","gui"])
            self.params_loading_settings.add_spacer(1,30)
            self.params_loading_settings.add_dropdown_button("extras","Extra...",options=["Tutorial"],index_values=["tutorial"])
        self.params_loading_settings.vs["load_settings"].connect(self.on_load_settings_button)
        self.params_loading_settings.vs["save_settings"].connect(self.on_save_settings_button)
        self.params_loading_settings.vs["extras"].connect(self.call_extra)

    closed=Signal()
    def closeEvent(self, event):
        self.closed.emit()
        return super().closeEvent(event)
            
    @controller.exsafeSlot()
    def on_load_settings_button(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,"Load GUI settings...",filter="Config Files (*.cfg);;Data Settings Files (*.dat);;All Files (*)",directory=self.v["defaults/settings_folder"])
        if path:
            self.v["defaults/settings_folder"]=os.path.split(path)[0]
            self.load_settings(path,scope=self.v["settings_load_scope"],cam_apply=True)
    @controller.exsafeSlot()
    def on_save_settings_button(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,"Load GUI settings...",filter="Config Files (*.cfg);;Data Settings Files (*.dat);;All Files (*)",directory=self.v["defaults/settings_folder"])
        if path:
            self.v["defaults/settings_folder"]=os.path.split(path)[0]
            self.save_settings(path)
    def show_tutorial_box(self):
        self.tutorial_box=tutorial.TutorialBox()
        self.tutorial_box.setup(self)
        self.tutorial_box.show()
    @controller.exsafeSlot(object)
    def call_extra(self, value):
        if value=="tutorial":
            if self.tutorial_box is None:
                self.show_tutorial_box()
            elif not self.tutorial_box.isVisible():
                self.tutorial_box.close()
                self.show_tutorial_box()
            else:
                self.tutorial_box.showNormal()

    _ext_controller_names={"camera":cam_thread,"processor":process_thread,"preprocessor":preprocess_thread,"saver":save_thread,"snap_saver":snap_save_thread,
        "slowdown":slowdown_thread,"channel_accumulator":channel_accumulator_thread,"settings_manager":settings_manager_thread,"resource_manager":resource_manager_thread}
    def _ordered_plugins(self):
        return sorted(self._running_plugins.items(),key=lambda v: v[1].start_order)
    def _sync_plugins(self, exec_point="plugin_setup"):
        for plugin in list(self._running_plugins.values()):
            plugin.ctl.sync_exec_point(exec_point)
    def _notify_plugins(self):
        notified=[]
        last_order=None
        for _,plugin in self._ordered_plugins():
            if last_order is not None and plugin.start_order!=last_order:
                for ctl in notified:
                    ctl.sync_exec_point("run")
            if plugin.notifier is not None:
                plugin.notifier.notify()
            notified.append(plugin.ctl)
            last_order=plugin.start_order
    def load_config_plugins(self):
        """Load all plugins described in the configuration file"""
        plugins_list=[]
        if "plugins" in self.settings:
            for p in sorted(self.settings["plugins"]):
                if "class" in self.settings["plugins",p]:
                    class_name=self.settings["plugins",p,"class"]
                    name=self.settings.get(("plugins",p,"name"),p)
                    parameters=self.settings.get(("plugins",p,"parameters"),None)
                    plugin_class=self._plugin_classes[class_name]
                    start_order=self.settings.get(("plugins",p,"start_order"),plugin_class._default_start_order)
                    plugins_list.append((plugin_class,name,parameters,start_order))
        plugins_list.sort(key=lambda v: v[-1])
        last_order=None
        for plugin_class,name,parameters,start_order in plugins_list:
            if last_order is not None and start_order!=last_order:
                self._sync_plugins()
            self.load_plugin(plugin_class,name=name,parameters=parameters,start_order=start_order)
            last_order=start_order
    PluginInfo=collections.namedtuple("PluginInfo",("ctl","notifier","start_order"))
    @controller.call_in_gui_thread
    def load_plugin(self, plugin_class, name="__default__", parameters=None, start_order=0):
        """
        Start plugin thread.

        Args:
            plugin_class: class of the plugin (subclass of :cls:`.IPlugin`)
            name: plugin name (for the cases of several plugins of the same class)
            parameters: additional plugin parameters
        """
        full_name=plugin_class.get_class_name(),name
        if full_name in self._running_plugins:
            raise RuntimeError("plugin {}.{} is already running".format(*full_name))
        notifier=synchronizing.QThreadNotifier() if not self._running else None
        plugin_ctl=plugins.PluginThreadController("plugin.{}.{}".format(*full_name),kwargs={"name":name,"main_frame":self,"notifier":notifier,
            "plugin_cls":plugin_class,"ext_controller_names":self._ext_controller_names,"parameters":parameters})
        self._running_plugins[full_name]=self.PluginInfo(plugin_ctl,notifier,start_order)
        plugin_ctl.start()
    @controller.call_in_gui_thread
    def initialize_plugin(self, plugin):
        """
        Initialize plugin.

        Called automatically by the plugin thread after plugin has been set up.
        """
        full_name=plugin.get_class_name(),plugin.get_instance_name()
        if full_name in self._plugin_parameters:
            values=self._plugin_parameters[full_name]
            plugin.set_all_values(values)
        plugin.start_gui()
    @controller.call_in_gui_thread
    def finalize_plugin(self, plugin):
        """
        Finalize plugin.

        Called automatically by the plugin thread after plugin has been stopped and cleaned up.
        """
        full_name=plugin.get_class_name(),plugin.get_instance_name()
        values=plugin.get_all_values()
        if full_name in self._plugin_parameters:
            del self._plugin_parameters[full_name]
        self._plugin_parameters[full_name]=values
        del self._running_plugins[full_name]

    def set_gui_level(self, level):
        """Set GUI detail level (either ``"full"`` for all controls, or ``"simplified"`` for essentials)"""
        self.gui_level=level
        if level=="simple":
            self.control_tabs.remove_tab("proc_tab")
            self.saving_settings_table.params.set_visible(["event_msg","log_event"],False)
    def _update_plugin_parameters(self):
        """Update ``_plugin_parameters`` attribute to reflect current plugin parameters"""
        for name,plugin in self._ordered_plugins():
            if plugin.ctl.is_plugin_running():
                par=plugin.ctl.get_all_values()
                self._plugin_parameters.add_entry(name,par,force=True)
    def _apply_plugin_parameters(self):
        """Apply values in the ``_plugin_parameters`` attribute to all running plugins"""
        for name,plugin in self._ordered_plugins():
            if plugin.ctl.is_plugin_running() and name in self._plugin_parameters:
                plugin.ctl.set_all_values(self._plugin_parameters[name])
    def get_all_values(self, full_status=False):
        """
        Get all GUI parameters (taking into account GUI level).
        
        If ``full_status==True``, also include status tables and GUI indicator values are stored.
        """
        values=super().get_all_values()
        self._update_plugin_parameters()
        values.add_entry("plugins",self._plugin_parameters,force=True)
        if full_status:
            values["indicators"]=self.get_all_indicators()
        else:
            for k in ["camstat","savestat"]:
                if ("cam",k) in values:
                    del values["cam",k]
        return values
    def set_all_values(self, values):
        """Set all GUI parameters (taking into account GUI level)"""
        if "plugins" in values:
            self._plugin_parameters=values.detach("plugins")
            self._apply_plugin_parameters()
        super().set_all_values(values)
        self.image_proc_indicator.update_indicators()

    def load_settings(self, path=None, warn_if_missing=True, scope="all", cam_apply=False):
        if path is None:
            path=_defaults_filename
        if os.path.exists(path):
            settings=loadfile.load_dict(path)
            if "gui" in settings:  # data stored settings file
                ver=settings.get("software/version",None)
                cam=settings.get("cfg/select_camera",None)
                if ver is None:
                    warn_msg="settings file does not contain the software version"
                elif ver!=version:
                    warn_msg="settings file version ({}) is different from the current version ({})".format(ver,version)
                elif cam is None:
                    warn_msg="settings file does not contain the camera name"
                elif cam!=self.cam_name:
                    warn_msg="settings file camera ({}) is different from the current camera ({})".format(cam,self.cam_name)
                else:
                    warn_msg=None
                if warn_msg is not None and warn_if_missing:
                    result=QtWidgets.QMessageBox.warning(self,"Incompatible settings format","Warning: {}; load anyway?".format(warn_msg),QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
                    if result==QtWidgets.QMessageBox.No:
                        return
                settings=settings["gui"]
            elif self.cam_name in settings:
                settings=settings[self.cam_name]
            else:
                if warn_if_missing:
                    QtWidgets.QMessageBox.warning(self,"Missing settings in the file","Warning: either loading not a settings file, or it contains settings for different cameras",QtWidgets.QMessageBox.Ok)
                settings={}
            if scope=="gui" and "cam/cam" in settings:
                del settings["cam/cam"]
            if scope=="camera":
                settings=dictionary.Dictionary({"cam/cam":settings.get("cam/cam",{})})
            self.set_all_values(settings)
            if cam_apply and scope in {"all","camera"}:
                self.cam_ctl.send_parameters()
            return True
        return False
    @controller.exsafe
    def save_settings(self, path=None):
        if path is None:
            path=_defaults_filename
        if os.path.exists(path):
            settings=loadfile.load_dict(path)
        else:
            settings=dictionary.Dictionary()
        if self.cam_name in settings:
            del settings[self.cam_name]
        settings[self.cam_name]=self.get_all_values()
        savefile.save_dict(settings,path)
    @controller.exsafeSlot()
    def start(self):
        self._sync_plugins()
        controller.sync_controller(cam_thread)
        first_time=not self.load_settings(warn_if_missing=False)
        super().start()
        self._notify_plugins()
        if first_time:
            self.show_tutorial_box()
    @controller.exsafeSlot()
    def stop(self):
        if self._running:
            self.save_settings()
        for plugin in list(self._running_plugins.values()):
            plugin.ctl.stop(sync=True)
        super().stop()



class CamSelectFrame(param_table.ParamTable):
    @controller.exsafe
    def setup(self, settings):
        super().setup(name="camera_select",add_indicator=False)
        self.setMinimumWidth(300)
        self.setWindowTitle("Camera select...")
        self.selected=False # prevents double-call on multiple clicks
        cameras=settings["cameras"]
        cam_ids=list(cameras)
        cam_names=[cameras[k].get("display_name",k) for k in cam_ids]
        self.add_combo_box("camera",label="Select camera:",options=cam_names,index_values=cam_ids)
        self.button_box=QtWidgets.QDialogButtonBox(self)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Close|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setCenterButtons(True)
        self.add_to_layout(self.button_box,location=("next",0,1,"end"))
        self.button_box.accepted.connect(lambda: self.on_select(True))
        self.button_box.rejected.connect(lambda: self.on_select(False))
    camera_selected=Signal(object)
    def on_select(self, accepted):
        if not self.selected:
            self.selected=True
            if accepted:
                self.camera_selected.emit(self.v["camera"])
            self.close()


### Camera kinds ###
TCameraKind=collections.namedtuple("TCameraKind",["devthread","controller","status"])
def_controller=GenericCamera_ctl.GenericCameraSettings_GUI
def_status=GenericCamera_ctl.GenericCameraStatus_GUI
camera_kinds={
    "AndorSDK2": TCameraKind(devthread.AndorSDK2CameraThread, def_controller, def_status),
    "AndorSDK2IXON": TCameraKind(devthread.AndorSDK2IXONThread, GenericCamera_ctl.IXONCameraSettings_GUI, GenericCamera_ctl.IXONCameraStatus_GUI),
    "AndorSDK2Luca": TCameraKind(devthread.AndorSDK2LucaThread, GenericCamera_ctl.LucaCameraSettings_GUI, GenericCamera_ctl.LucaCameraStatus_GUI),
    "AndorSDK3": TCameraKind(devthread.AndorSDK3CameraThread, def_controller, def_status),
    "AndorSDK3Zyla": TCameraKind(devthread.AndorSDK3ZylaThread, GenericCamera_ctl.ZylaCameraSettings_GUI, GenericCamera_ctl.ZylaCameraStatus_GUI),
    "DCAM": TCameraKind(devthread.DCAMCameraThread, GenericCamera_ctl.DCAMCameraSettings_GUI, def_status),
    "DCAMOrca": TCameraKind(devthread.DCAMOrcaCameraThread, GenericCamera_ctl.DCAMCameraSettings_GUI, def_status),
    "DCAMImagEM": TCameraKind(devthread.DCAMImagEMCameraThread, GenericCamera_ctl.DCAMImagEMCameraSettings_GUI, def_status),
    "PhotonFocusLAN": TCameraKind(devthread.EthernetPhotonFocusIMAQdxCameraThread, def_controller, def_status),
    "PhotonFocusIMAQ": TCameraKind(devthread.IMAQPhotonFocusCameraThread, GenericCamera_ctl.PhotonFocusIMAQCameraSettings_GUI, GenericCamera_ctl.PhotonFocusIMAQCameraStatus_GUI),
    "PhotonFocusSiSo": TCameraKind(devthread.SiliconSoftwarePhotonFocusCameraThread, GenericCamera_ctl.PhotonFocusSiliconSoftwareCameraSettings_GUI, GenericCamera_ctl.PhotonFocusSiliconSoftwareCameraStatus_GUI),
    "PCOSC2": TCameraKind(devthread.PCOCameraThread, GenericCamera_ctl.PCOCameraSettings_GUI, def_status),
    "Picam": TCameraKind(devthread.PicamCameraThread, GenericCamera_ctl.PicamCameraSettings_GUI, def_status),
    "UC480": TCameraKind(devthread.UC480CameraThread, GenericCamera_ctl.UC480CameraSettings_GUI, GenericCamera_ctl.UC480CameraStatus_GUI),
    "ThorlabsTLCam": TCameraKind(devthread.ThorlabsTLCameraThread, GenericCamera_ctl.ThorlabsTLCameraSettings_GUI, def_status),
}


### Command line arguments ###
parser=argparse.ArgumentParser(description="Pylablib cam-control software for controlling all connected cameras")
parser.add_argument("--camera","-c", help="controlled camera name",metavar="CAM_NAME")
parser.add_argument("--config-file","-cf", help="configuration file path",metavar="FILE",default="settings.cfg")
argvp=parser.parse_args()


### Main execution ###
if __name__=="__main__":
    with controller.exint(): # catching exception
        # Load config file, or generate a new one
        if os.path.exists(argvp.config_file):
            settings=loadfile.load_dict(argvp.config_file)
            cameras_present="cameras" in settings
            if "dlls" in settings:
                for k,v in settings["dlls"].items():
                    pylablib.par["devices/dlls",k]=v
        else:
            cameras_present=False
        if not cameras_present:
            import detect
            print("No cameras in the config file; running autodetect")
            detect.update_settings_file(argvp.config_file,verbose=True)
            settings=loadfile.load_dict(argvp.config_file)
        settings["runtime/root_folder"]=os.path.abspath(".") if __name__=="__main__" else ""
        ncams=len(settings.get("cameras",[]))
        if ncams==0: # Show a message and exit
            print("No cameras in the configuration file")
            input("Press Enter to continue")
        else:

            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling,True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps,True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_Use96Dpi,True)

            # Create forms
            app=QtWidgets.QApplication(sys.argv)
            app.setStyleSheet(color_theme.load_style(settings.get("interface/color_theme","dark")))
            main_form=StandaloneFrame()
            select_form=CamSelectFrame()

            # Create and launch thread controllers
            gui=controller.get_gui_controller()
            services.FrameBinningThread(preprocess_thread,kwargs={"src":cam_thread,"tag_in":"frames/new"}).start()
            services.FrameSlowdownThread(slowdown_thread,kwargs={"src":preprocess_thread,"tag_in":"frames/new"}).start()
            services.FrameProcessorThread(process_thread,kwargs={"src":slowdown_thread,"tag_in":"frames/new"}).start()
            services.ChannelAccumulator(channel_accumulator_thread,kwargs={"settings":settings.get("interface/trace_plotter")}).start()
            services.FrameSaveThread(save_thread,kwargs={"src":preprocess_thread,"tag":"frames/new","settings_mgr":settings_manager_thread,"frame_processor":process_thread}).start()
            services.FrameSaveThread(snap_save_thread,kwargs={"src":"any","tag":"frames/new/snap","settings_mgr":settings_manager_thread}).start()
            services.SettingsManager(settings_manager_thread).start()
            services.ResourceManager(resource_manager_thread).start()

            @controller.exsafeSlot(object)
            def start_main_form(cam_name=None):
                settings_ctl=controller.sync_controller(settings_manager_thread)
                cam_name=cam_name or settings["select_camera"]
                if cam_name not in settings["cameras"]:
                    raise ValueError("unavailable camera {}".format(cam_name))
                if ("css",cam_name) in settings:
                    settings.update(settings["css",cam_name])
                channel_accum=controller.sync_controller(channel_accumulator_thread)
                channel_accum.cs.add_source("raw",src=preprocess_thread,tag="frames/new",sync=True,kind="raw")
                channel_accum.cs.add_source("show",src=process_thread,tag="frames/new/show",sync=True,kind="show")
                cam_kind=camera_kinds[settings["cameras",cam_name,"kind"]]
                cam_ctl=cam_kind.devthread(cam_thread,kwargs=settings["cameras",cam_name,"params"].as_dict())
                cam_ctl.start()
                main_form.setup(settings=settings,cam_name=cam_name)
                settings_ctl.ca.update_settings("software/version",version)
                settings_ctl.ca.add_source("cam",cam_ctl.cs.get_full_info)
                settings_ctl.ca.add_source("cam/settings",cam_ctl.cs.get_settings)
                def get_cam_counters():
                    counters=cam_ctl.v["frames"]
                    if "last_frame" in counters:
                        del counters["last_frame"]
                    return counters
                settings_ctl.ca.add_source("cam/cnt",get_cam_counters)
                image_saver=controller.sync_controller(save_thread)
                image_saver.ca.setup_queue_ram(settings.get("saving/max_queue_ram",4*2**30))
                main_form.start()
                main_form.show()
            @controller.exsafeSlot()
            def start_select_form():
                select_form.setup(settings=settings)
                select_form.camera_selected.connect(start_main_form)
                select_form.show()

            # Figuring out default camera
            ncams=len(settings.get("cameras",[]))
            if ncams==1:
                settings["select_camera"]=list(settings["cameras"].keys())[0]
            if argvp.camera:
                settings["select_camera"]=argvp.camera

            # Setting up a form start event
            if "select_camera" in settings:
                gui.started.connect(start_main_form)
            else:
                gui.started.connect(start_select_form)
            # Start the GUI event loop
            app.exec_()
    os.chdir(startdir)