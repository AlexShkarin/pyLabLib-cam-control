from pylablib.core.gui.widgets import container, param_table
from pylablib.core.thread import controller


class FramePreproccessBinning_GUI(container.QGroupBoxContainer):
    """
    Frame preprocessing settings controller widget.

    Controls time and space binning parameters.
    """
    def setup(self, preprocess_thread):
        super().setup(caption="Acquisition binning",no_margins=True)
        # Setup threads
        self.image_preprocessor=controller.sync_controller(preprocess_thread)
        # Setup GUI
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup(add_indicator=False)
        bin_modes=["mean","sum","min","max","skip"]
        bin_mode_names=["Mean","Sum","Min","Max","Skip"]
        self.params.add_combo_box("spat_bin_mode",options=bin_mode_names,index_values=bin_modes,value="mean",label="Spatial binning mode:")
        with self.params.using_new_sublayout("spat_bin_box","hbox"):
            self.params.add_num_edit("spat_bin_x",label="X:",formatter="int",limiter=(1,None,"coerce","int"),value=1)
            self.params.add_num_edit("spat_bin_y",label="Y:",formatter="int",limiter=(1,None,"coerce","int"),value=1)
            self.params.add_padding()
        self.params.add_spacer(0)
        self.params.add_combo_box("time_bin_mode",options=bin_mode_names,index_values=bin_modes,value="mean",label="Temporal binning mode:")
        with self.params.using_new_sublayout("time_bin_box","hbox"):
            self.params.add_num_edit("time_bin",label="T:",formatter="int",limiter=(1,None,"coerce","int"),value=1)
            self.params.add_padding()
        self.params.add_spacer(0)
        self.params.add_check_box("convert_to_float",caption="Convert frame to float")
        self.params.add_toggle_button("bin_enabled",caption="Enable binning")
        @controller.exsafe
        def setup_binning():
            spat_bin=self.v["spat_bin_x"],self.v["spat_bin_y"]
            spat_bin_mode=self.v["spat_bin_mode"]
            time_bin=self.v["time_bin"]
            time_bin_mode=self.v["time_bin_mode"]
            convert_to_float=self.v["convert_to_float"]
            self.image_preprocessor.ca.setup_binning(spat_bin,spat_bin_mode,time_bin,time_bin_mode,dtype="float" if convert_to_float else None)
        for ctl in ["spat_bin_mode","spat_bin_x","spat_bin_y","time_bin_mode","time_bin","convert_to_float"]:
            self.params.vs[ctl].connect(setup_binning)
        setup_binning()
        self.params.vs["bin_enabled"].connect(self.enable_binning)
        self.params.add_padding("horizontal",location=(0,"next","end",1))
        self.params.layout().setColumnStretch(1,0)
        for ctl in ["spat_bin_x","spat_bin_y","time_bin"]:
            self.params.w[ctl].setMaximumWidth(70)
    def start(self):
        self.ctl.call_thread_method("add_activity","processing","binning",caption="Binning",short_cap="Bin",order=0)
        super().start()
    def enable_binning(self, enable):
        self.image_preprocessor.ca.enable_binning(enable)
        self.ctl.call_thread_method("update_activity_status","processing","binning",status="on" if enable else "off")


class FramePreproccessSlowdown_GUI(container.QGroupBoxContainer):
    """
    Frame slowdown settings controller widget.

    Controls target FPS and slowdown buffer size.
    """
    def setup(self, slowdown_thread):
        super().setup(caption="Slowdown",no_margins=True)
        # Setup threads
        self.frame_slowdown=controller.sync_controller(slowdown_thread)
        # Setup GUI
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup()

        self.params.add_num_label("source_fps",formatter=".1f",label="Source FPS:")
        self.params.add_num_edit("slowdown_fps",formatter=".1f",limiter=(1,None,"coerce"),value=10,label="Target FPS:")
        self.params.add_num_edit("slowdown_buffer",formatter="int",limiter=(1,None,"coerce","int"),value=100,label="Slowdown buffer:")
        self.params.add_toggle_button("slowdown_enabled",caption="Slowdown",add_indicator=False)
        @controller.exsafe
        def setup_slowdown():
            self.frame_slowdown.ca.setup_slowdown(self.v["slowdown_fps"],self.v["slowdown_buffer"])
        for ctl in ["slowdown_fps","slowdown_buffer"]:
            self.params.vs[ctl].connect(setup_slowdown)
        setup_slowdown()
        self.params.vs["slowdown_enabled"].connect(lambda v: self.frame_slowdown.ca.enable(v))
        self.params.add_padding("horizontal",location=(0,"next","end",1))
        self.params.layout().setColumnStretch(1,0)
        for ctl in ["slowdown_fps","slowdown_buffer"]:
            self.params.w[ctl].setMaximumWidth(70)
        # Timer
        self.add_timer_event("recv_parameters",self.recv_parameters,period=0.5)
    def recv_parameters(self):
        """Update slowdown indicators"""
        self.v["source_fps"]=self.frame_slowdown.v["fps/in"]
        self.i["slowdown_fps"]=self.frame_slowdown.v["fps/out"]
        self.i["slowdown_buffer"]="{} / {}".format(self.frame_slowdown.v["buffer/used"],self.frame_slowdown.v["buffer/filled"])
        if self.frame_slowdown.v["buffer/empty"]:
            self.v["slowdown_enabled"]=False