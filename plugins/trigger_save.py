from . import base
from pylablib.core.thread import controller
# from pylablib.devices import NI, Conrad

import numpy as np
import time


class TriggerSavePlugin(base.IPlugin):
    """
    Plugin for automatic starting of saving either on timer, or on maximal value of a plotted frame.
    """
    _class_name="trigger_save"
    _default_start_order=10
    def setup(self):
        self._last_save_timer=None
        self._last_save_image=None
        self._acquired_videos=None
        self._trigger_display_time=0.5
        self.trig_modes=["timer","image"]
        self._frame_sources={}
        self.extctls["resource_manager"].cs.add_resource("process_activity","saving/"+self.full_name,ctl=self.ctl,
            caption="Trigger save",short_cap="Trg",order=10)
        self.setup_gui_sync()
        self.ctl.subscribe_commsync(lambda *args: self._update_frame_sources(),
            srcs=self.extctls["resource_manager"].name,tags=["resource/added","resource/removed"])
        self._update_frame_sources(reset_value=True)
        self.ctl.add_job("check_timer_trigger",self.check_timer_trigger,0.1)
        self.ctl.add_command("toggle",self.toggle)
        self.ctl.v["enabled"]=False
    
    def setup_gui(self):
        self.table=self.gui.add_plugin_box("params","Save trigger",cache_values=True)
        self.table.add_combo_box("save_mode",options=["Full","Snap"],index_values=["full","snap"],label="Save mode")
        self.table.add_check_box("limit_videos",caption="Limit number of videos",value=False)
        self.table.add_num_edit("max_videos",1,limiter=(1,None,"coerce","int"),formatter="int",label="Number of videos",add_indicator=True)
        trig_mode_names={"timer":"Timer","image":"Image"}
        self.table.add_combo_box("trigger_mode",options=[trig_mode_names[m] for m in self.trig_modes],index_values=self.trig_modes,label="Trigger mode")
        self.table.add_num_edit("period",10,limiter=(.1,None,"coerce"),formatter=("float","auto",1),label="Timer period (s)")
        self.table.add_combo_box("frame_source",options=[],label="Trigger frame source")
        self.table.add_num_edit("image_trigger_threshold",0,formatter=("float","auto",4),label="Trigger threshold")
        self.table.add_num_edit("dead_time",10,limiter=(0,None,"coerce"),formatter=("float","auto",1),label="Dead time (s)")
        self.table.add_text_label("event_trigger_status","armed",label="Event trigger status: ")
        self.table.add_toggle_button("enabled","Enabled",value=False)
        self.table.vs["limit_videos"].connect(lambda v: self.table.set_enabled("max_videos",v))
        self.table.set_enabled("max_videos",False)
        @controller.exsafe
        def reset_acquired_videos():
            self.table.i["max_videos"]=self._acquired_videos=0
            self._last_video=False
        self.table.vs["enabled"].connect(reset_acquired_videos)
        reset_acquired_videos()
        @controller.exsafe
        def setup_gui_state():
            trigger_mode=self.table.v["trigger_mode"]
            self.table.set_enabled("period",trigger_mode=="timer")
            self.table.set_enabled("dead_time",trigger_mode!="timer")
            self.table.set_enabled("frame_source",trigger_mode=="image")
            self.table.set_enabled("image_trigger_threshold",trigger_mode=="image")
            self.table.set_enabled("enabled",not (trigger_mode=="image" and self.table.v["frame_source"]==-1))
            self._update_trigger_status("armed")
        self.table.vs["trigger_mode"].connect(setup_gui_state)
        self.table.vs["frame_source"].connect(setup_gui_state)
        setup_gui_state()

    def _update_frame_sources(self, update_subscriptions=True, reset_value=None):
        sources=self.extctls["resource_manager"].cs.list_resources("frame/display")
        sources={n:v for n,v in sources.items() if "src" in v and "tag" in v}
        if update_subscriptions:
            for n in list(self._frame_sources):
                if n not in sources:
                    self.ctl.unsubscribe(self._frame_sources.pop(n))
            def make_frame_recv_func(src):
                return lambda s,t,m: self.check_frame_trigger(src,m.last_frame())
            for n,v in sources.items():
                if n not in self._frame_sources:
                    sid=self.ctl.subscribe_commsync(make_frame_recv_func(n),srcs=v["src"],tags=v["tag"],limit_queue=1)
                    self._frame_sources[n]=sid
        self._update_frame_sources_indicator(sources,reset_value=reset_value)
    @controller.call_in_gui_thread
    def _update_frame_sources_indicator(self, sources, reset_value=False):
        index_values,options=zip(*[(n,v.get("caption",n)) for n,v in sources.items()])
        self.table.w["frame_source"].set_options(options=options,index_values=index_values,value=index_values[0] if reset_value else None)
    @controller.call_in_gui_thread
    def _start_save(self, mode):
        self.guictl.call_thread_method("toggle_saving",mode=mode,start=True,no_popup=True)
        self._acquired_videos+=1
        self.table.i["max_videos"]=self._acquired_videos
        if self._acquired_videos>=self.table.v["max_videos"] and self.table.v["limit_videos"]:
            self._last_video=True
    def _saving_in_progress(self):
        saving_status=self.extctls["resource_manager"].cs.get_resource("process_activity","saving/streaming").get("status","off")
        return saving_status!="off"
    def check_timer_trigger(self):
        """Check saving timer and start saving if it's passed"""
        enabled=self.table.v["enabled"]
        self.ctl.v["enabled"]=enabled
        if enabled and self.table.v["trigger_mode"]=="timer":
            t=time.time()
            if not (self._saving_in_progress() or self._last_video) and (self._last_save_timer is None or t>self._last_save_timer+self.table.v["period"]):
                self._start_save(self.table.v["save_mode"])
                self._last_save_timer=t
        else:
            self._last_save_timer=None
        self.extctls["resource_manager"].csi.update_resource("process_activity","saving/"+self.full_name,status="on" if enabled else "off")
        if self._last_video and not self._saving_in_progress():
            self.toggle(enable=False)
    def _update_trigger_status(self, status):
        if self.table.v["event_trigger_status"]!=status: # check (cached) value first to avoid unnecessary calls to GUI thread
            self.table.v["event_trigger_status"]=status
    def check_frame_trigger(self, src, frame):
        """Check incoming image and start saving if it's passed"""
        dead_time=self.table.v["dead_time"] if self.table.v["enabled"] else 0
        t=time.time()
        if self.table.v["trigger_mode"]=="image":
            if self.table.v["frame_source"]==src:
                if self._last_save_image is None or t>self._last_save_image+dead_time:
                    if np.any(frame>self.table.v["image_trigger_threshold"]):
                        if not (self._saving_in_progress() or self._last_video) and self.table.v["enabled"]:
                            self._start_save(self.table.v["save_mode"])
                        self._last_save_image=t
                if self._last_save_image is not None and t<self._last_save_image+self._trigger_display_time:
                    self._update_trigger_status("triggered")
                elif self._last_save_image is not None and t<self._last_save_image+dead_time:
                    self._update_trigger_status("dead time")
                else:
                    self._update_trigger_status("armed")
        else:
            self._last_save_image=None
    
    @controller.call_in_gui_thread
    def toggle(self, enable=True):
        """Enable or disable the measurement"""
        self.ctl.v["enabled"]=self.table.v["enabled"]=enable

    def set_all_values(self, values):
        self._update_frame_sources(update_subscriptions=False)
        if "params/enabled" in values:
            del values["params/enabled"]
        super().set_all_values(values)