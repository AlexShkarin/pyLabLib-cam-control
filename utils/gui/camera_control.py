from pylablib.core.thread import controller
from pylablib.core.gui.widgets import container
from pylablib.thread.stream.stream_message import FramesMessage

from pylablib.core.gui import Signal
import numpy as np


class GenericCameraCtl(container.QContainer):
    """
    Generic GUI controller for cameras.

    Manages intraction between camera thread, saving thread, and GUI widgets:
    camera image view (with its own control), camera param table, camera status table, and saving controls.

    Interaction with widgets is mainly done through 4 widget methods:
        collect_parameters: get parameters from the widget as a dictionary
        show_parameters: send parameter to the widget as a dictionary
        get_all_values: get all widget GUI values (used only for saving/loading parameters from file)
        set_all_values: set all widget GUI values (used only for saving/loading parameters from file)
    
    In addition, widget classes can connect controller methods to some of the GUI events (usually, button clicks).
    """
    def __init__(self, cam_thread="camera", frame_src_thread=None, save_thread=None, snap_save_thread=None, preprocess_thread=None, resource_manager_thread=None, frame_tag="frames/new", cam_name=None, settings=None):
        super().__init__()
        self.cam_thread=cam_thread
        self.dev=None
        self.save_thread=save_thread
        self.snap_save_thread=snap_save_thread
        self.preprocess_thread=preprocess_thread
        self.resource_manager_thread=resource_manager_thread
        self.frame_src_thread=frame_src_thread or cam_thread
        self.cam_name=cam_name
        self.settings=settings or {}
        self.frame_tag=frame_tag
        self.no_popup=False
    
    def setup(self):
        super().setup()
        self.saver=controller.sync_controller(self.save_thread,"start") if self.save_thread else None
        self.snap_saver=controller.sync_controller(self.snap_save_thread,"start") if self.snap_save_thread else None
        self.resource_manager=controller.sync_controller(self.resource_manager_thread) if self.resource_manager_thread else None
        self.ctl.subscribe_sync(self.receive_frame,self.frame_src_thread,tags=self.frame_tag,limit_queue=1)
        self.ctl.subscribe_sync(lambda *args: self.recv_parameters(),self.cam_thread,tags="status/connection",filt=lambda s,d,t,v: v=="opened")
        self.ctl.subscribe_sync(lambda src,tag,val: self.plot_control(*val),tags="image_plotter/control",limit_queue=-1)
        if self.resource_manager is not None:
            self.resource_manager.cs.add_resource("frame/display","raw",caption="Raw",src=self.frame_src_thread,tag=self.frame_tag,frame=None)
            self.ctl.subscribe_sync(lambda *args: self.frames_sources_updates.emit(),srcs=self.resource_manager_thread,tags=["resource/added","resource/removed"])
        self.ctl.add_thread_method("toggle_saving",self.toggle_saving)
        self.ctl.add_thread_method("get_saving_parameters",lambda mode="full": self.c["savebox"].collect_parameters(mode))
        self.ctl.add_thread_method("dev_connect",self.dev_connect)
        self.ctl.add_thread_method("dev_disconnect",self.dev_disconnect)
        self.ctl.add_thread_method("acq_start",self.acq_start)
        self.ctl.add_thread_method("acq_stop",self.acq_stop)
        self.ctl.add_thread_method("clear_pretrigger",self.clear_pretrigger)
        self.initialized=False
        self._last_parameters={}
        self._last_shown_frame=None
        self.add_timer_event("recv_parameters",self.recv_parameters,period=0.5)

    def start(self):
        """Start update timer"""
        self.dev=controller.sync_controller(self.cam_thread,"start")
        if "camstat" in self.c and self.cam_name is not None:
            self.v["camstat/cam_name"]=self.settings.get(("cameras",self.cam_name,"display_name"),self.cam_name)
            self.v["camstat/cam_kind"]=self.settings.get(("cameras",self.cam_name,"kind"),"")
        self.setup_pretrigger()
        super().start()
    
    @controller.exsafe
    def dev_connect(self):
        """Connect to device (connected to a button in camera control)"""
        if self.dev is not None:
            self.dev.ca.open(reopen=True)
    @controller.exsafe
    def dev_disconnect(self):
        """Disconnect from the device (connected to a button in camera control)"""
        if self.dev is not None:
            self.dev.ca.close(keep_closed=True)
    @controller.exsafe
    def acq_start(self):
        """Start acquisition (connected to a button in camera control)"""
        if self.dev is not None:
            self.dev.ca.acq_start()
    @controller.exsafe
    def acq_stop(self):
        """Stop acquisition (connected to a button in camera control)"""
        if self.dev is not None:
            self.dev.ca.acq_stop()
    @controller.exsafe
    def toggle_saving(self, mode, start=True, source=None, change_params=None, no_popup=False):
        """
        Turn saving on/off (connected to a button in saving control)
        
        `mode` is the saving mode: either ``"full"`` (full stream saving), or ``"snap"`` (snapshot saving).
        If `change_params` is defined, it is a dictionary which overrides some of the saving parameters from the GUI.
        """
        if (self.saver and mode=="full") or (self.snap_saver and mode=="snap"):
            self.no_popup=no_popup
            if start:
                params=self.settings.get("saving/defaults",{})
                params.update(self.c["savebox"].collect_parameters(mode=mode))
                if params["path"] is None: # invalid path
                    return
                params.update(change_params or {})
            perform_status_check=False
            if mode=="full":
                if start:
                    if "settings" in self.c:
                        perform_status_check=self.c["settings"].collect_parameters().get("perform_status_check",False)
                    self.saver.csi.save_start(params["path"],path_kind=params["path_kind"],batch_size=params["batch_size"],
                        append=params["append"],format=params["format"],filesplit=params["filesplit"],
                        save_settings=params["save_settings"],perform_status_check=perform_status_check)
                else:
                    self.saver.ca.save_stop()
            else:
                if start:
                    self.snap_saver.csi.save_start(params["path"],path_kind=params["path_kind"],batch_size=1,append=False,
                        format=params["format"],save_settings=params["save_settings"])
                    self.send_snap_frame(source=source or params["snap_display_source"])
                else:
                    self.snap_saver.ca.save_stop()
            self.recv_parameters(update={"status/saving":"in_progress"} if start else None)
    frames_sources_updates=Signal()
    def get_frame_sources(self):
        """Get a dictionary ``{name: caption}`` of all frame sources for the snap saving"""
        if self.resource_manager:
            sources=self.resource_manager.cs.list_resources("frame/display")
            return {n:v.get("caption",n) for n,v in sources.items()}
        else:
            return {"raw":"Raw"}
    def send_snap_frame(self, source=None):
        """Send a multicast with the source frame to the snap saver"""
        if self.resource_manager and source is not None:
            frame=self.resource_manager.cs.get_resource("frame/display",source,default={}).get("frame",None)
        else:
            frame=self._last_shown_frame
        if frame is not None:
            self.ctl.send_multicast(self.snap_save_thread,tag="frames/new/snap",value=FramesMessage([frame]))
    @controller.exsafe
    def write_event_log(self):
        """Write an event to the saving event log"""
        if self.saver:
            params=self.settings.get("saving/defaults",{})
            params.update(self.c["savebox"].collect_parameters(resolve_path=False))
            self.saver.ca.write_event_log(params["event_msg"])
    @controller.exsafe
    def setup_pretrigger(self):
        """Setup pretrigger according to the GUI saver settings"""
        if self.saver:
            params=self.settings.get("saving/defaults",{})
            params.update(self.c["savebox"].collect_parameters(resolve_path=False))
            self.saver.ca.setup_pretrigger(params["pretrigger_size"],params["pretrigger_enabled"])
    @controller.exsafe
    def clear_pretrigger(self):
        """Clear pretrigger buffer"""
        if self.saver:
            self.saver.ca.clear_pretrigger()
        
    # Obtain all parameters from the camera
    def get_thread_parameters(self):
        """Get parameters from the camera and saver threads and put them in form used by widgets"""
        if self.dev is None:
            return {}
        self.dev.sync_exec_point("run",timeout=20.)
        params=self.dev.get_variable("parameters") or {}
        if params:
            for s in ["frames/read","frames/acquired","frames/buffer_filled","frames/fps"]:
                params[s]=self.dev.v[s]
            if self.saver:
                params["status/saving"]=self.saver.get_variable("status/saving","stopped")
                for n in ["saved","missed","received","scheduled","queue_ram","max_queue_ram","pretrigger_status"]:
                    params["frames",n]=self.saver.get_variable(n,0)    
                params["frames/status_line_check"]=self.saver.get_variable("status_line_check","none")
        return params
    # Check camera parameters and setup the interface (called on timer)
    @controller.exsafe
    def recv_parameters(self, update=None):
        """Receive camera and saving parameters, and show them in widgets"""
        params=self.get_thread_parameters()
        params.update(update or {})
        if params:
            if "settings" in self.c:
                self.c["settings"].show_parameters(params)
            if "camstat" in self.c:
                self.c["camstat"].show_parameters(params)
            if "savebox" in self.c:
                self.c["savebox"].show_parameters(params)
            if "savestat" in self.c:
                self.c["savestat"].show_parameters(params)
            if not self.initialized:
                self.initialized=True
                self.send_parameters()
    # Send control parameters to the camera (called on Apply button press)
    @controller.exsafe
    def send_parameters(self, only_diff=False, dependencies=None):
        """
        Collect parameters from widgets and send it to the camera
        
        If ``only_diff==True``, only save parameters which are different from the last send.
        If dependencies` is not ``None``, it specifies dictionary ``{name: [deps]}`` with parameter dependencies;
        when parameter ``name`` is updated, all dependent parameters (in list ``[deps]``) should be updated as well (only applies if ``only_diff==True``).
        """
        if "settings" in self.c and self.initialized:
            params=self.c["settings"].collect_parameters()
            if only_diff:
                send_params=params.copy()
                for p in params:
                    if p in self._last_parameters and self._last_parameters[p]==params[p]:
                        del send_params[p]
                if dependencies:
                    dps=set()
                    for p in send_params:
                        if p in dependencies:
                            dps.update(set(dependencies[p]))
                    for dp in dps:
                        send_params[dp]=params[dp]
            else:
                send_params=params
            self.dev.ca.apply_parameters(send_params)
            self._last_parameters=params.copy()
    
    # Frame message receiver
    image_updated=Signal()
    def receive_frame(self, src, tag, msg):
        """Receive frame mutlicast from the camera and show the frame in the view window"""
        if "plotter_area" not in self.c:
            return
        frame=msg.last_frame()
        if "interface/plotter/binning/max_size" in self.settings:
            max_size=self.settings["interface/plotter/binning/max_size"]
            bin_mode=self.settings.get("interface/plotter/binning/mode","mean")
            binning=(max(frame.shape)-1)//max_size+1
            self.c["plotter_area"].set_binning(binning,binning,bin_mode,update_image=False)
        self.c["plotter_area"].set_image(frame)
        if self.c["plotter_area"].update_image(update_controls=True):
            self.image_updated.emit()
            self._last_shown_frame=frame
            if self.resource_manager:
                self.resource_manager.cs.update_resource("frame/display","raw",frame=frame)
    def plot_control(self, comm, val):
        """Process image plotting control messages (e.g., drawing commands)"""
        if "plotter_area" not in self.c:
            return
        comm=[t for t in comm.split("/") if t]
        if comm[0]=="rectangles":
            if comm[1]=="set":
                self.c["plotter_area"].set_rectangle(*val)
            elif comm[1]=="del":
                self.c["plotter_area"].del_rectangle(val)
            elif comm[1]=="show":
                self.c["plotter_area"].show_rectangles(True,names=val)
            elif comm[1]=="hide":
                self.c["plotter_area"].show_rectangles(False,names=val)
            else:
                raise ValueError("unrecognized rectangle command: {}".format(comm[1:]))
        else:
            raise ValueError("unrecognized rectangle command: {}".format(comm))

    # Loading and saving of parameters
    def get_all_values(self):
        """Get all GUI values as a dictionary"""
        settings=super().get_all_values()
        if "plotter_area" in self.c:
            settings["cam/img_size"]=self.c["plotter_area"].img.shape
        return settings
    def set_all_values(self, params):
        """Set all GUI values from a dictionary"""
        if "plotter_area" in self.c and "cam/img_size" in params:
            img=np.zeros(params["cam/img_size"])
            self.c["plotter_area"].set_image(img)
        super().set_all_values(params)
