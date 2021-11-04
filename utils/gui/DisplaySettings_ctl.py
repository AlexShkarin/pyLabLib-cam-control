from pylablib.core.gui.widgets import container, param_table
from pylablib.core.thread import controller

import time


class DisplaySettings_GUI(container.QGroupBoxContainer):
    """
    Display settings controller widget.

    Shows and controls display FPS, and notifies if a slowdown is active.

    Args:
        slowdown_thread: name of the frame slowdown thread, if applicable
        period_update_tag: tag of a multicast which is sent when the display update period is changed
    """
    _ignore_set_values={"slowdown_enabled"}
    def setup(self, slowdown_thread=None, period_update_tag="processing/control"):
        super().setup(caption="Display settings",no_margins=True)
        self.setMaximumWidth(200)
        self.slowdown_thread=slowdown_thread
        self.frame_slowdown=controller.sync_controller(self.slowdown_thread) if self.slowdown_thread else None
        # Setup GUI
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup(add_indicator=False)
        self.params.add_decoration_label("Display update period:",location=("next",0,1,2))
        self.params.add_num_edit("display_update_period",formatter=".3f",limiter=(0.01,None,"coerce"),value=0.05,location=(-1,2))
        self.params.add_num_label("display_fps",formatter=".3f",label="Display FPS:",value=0)
        self.params.add_text_label("slowdown_enabled",location=(-1,2,1,"end"))
        def set_display_period(period):
            if period_update_tag is not None:
                self.ctl.send_multicast(tag=period_update_tag,value=("display_update_period",period))
        self.params.vs["display_update_period"].connect(set_display_period)
        self._fps_update_period=1.
        self._last_fps_refresh=time.time()
        self._last_fps_cnt=0
        # Timer
        self.add_timer_event("update_params",self.update_params,period=0.5)
    def start(self):
        self.gui_values.update_value("display_update_period")
        super().start()

    def _refresh_fps(self):
        t=time.time()
        if self._last_fps_refresh+self._fps_update_period>t:
            self._last_fps_cnt+=1
        else:
            self.v["display_fps"]=(self._last_fps_cnt+1.)/(t-self._last_fps_refresh)
            self._last_fps_refresh=t
            self._last_fps_cnt=0
    def update_params(self):
        """Update parameters (display FPS indicator)"""
        t=time.time()
        if t>self._last_fps_refresh+2*self._fps_update_period:
            self.v["display_fps"]=self._last_fps_cnt/(t-self._last_fps_refresh)
            self._last_fps_refresh=t
            self._last_fps_cnt=0
    @controller.exsafeSlot()
    def on_new_frame(self):
        """Process generation of a new frame"""
        t=time.time()
        self._last_fps_cnt+=1
        if t>self._last_fps_refresh+self._fps_update_period:
            self.v["display_fps"]=self._last_fps_cnt/(t-self._last_fps_refresh)
            self._last_fps_refresh=t
            self._last_fps_cnt=0
        if self.frame_slowdown is not None and self.frame_slowdown.v["enabled"]:
            self.v["slowdown_enabled"]="slowdown"
            self.params.w["slowdown_enabled"].setStyleSheet("background: gold; font-weight: bold; color: black")
        else:
            self.v["slowdown_enabled"]=""
            self.params.w["slowdown_enabled"].setStyleSheet("")