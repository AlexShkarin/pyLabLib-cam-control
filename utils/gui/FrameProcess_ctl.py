from pylablib.core.gui.widgets import container, param_table
from pylablib.core.thread import controller
from pylablib.gui.widgets import range_controls


class FrameProccess_GUI(container.QGroupBoxContainer):
    """
    Frame processing settings controller widget.

    Controls enabling processing steps and triggering background acquisition.
    """
    def setup(self, process_thread, settings=None):
        super().setup(caption="Background subtraction",no_margins=True)
        # Setup threads
        self.process_thread=process_thread
        self.settings=settings or {}
        self.image_processor=controller.sync_controller(self.process_thread)
        self.image_processor.ca.load_settings(self.settings)
        # Setup GUI
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setMaximumWidth(260)
        self.params.setup(add_indicator=False)
        self.params.add_combo_box("method",options=["Snapshot","Running"],index_values=["snapshot","running"],label="Method:")
        self.params.add_num_edit("comb_count",formatter="int",limiter=(1,None,"coerce","int"),value=1,label="Frames count:",add_indicator=True)
        self.params.add_num_edit("comb_step",formatter="int",limiter=(1,None,"coerce","int"),value=1,label="Frames step:",add_indicator=True)
        self.params.add_combo_box("comb_mode",options=["Mean","Median","Min"],index_values=["mean","median","min"],label="Combination mode:")
        self.params.add_spacer(0)
        self.params.add_button("grab_background","Grab background",location=("next",0,1,1))
        self.params.add_text_label("background_state",location=(-1,1,1,"end"))
        with self.params.using_new_sublayout("background_saving_row","hbox"):
            self.params.add_combo_box("background_saving",options=["None","Only background","Background + source"],index_values=["none","background","all"],label="Snap save:")
            self.params.add_padding(stretch=1)
        self.params.add_spacer(5)
        self.params.add_toggle_button("enabled",caption="Enable subtraction")
        self.params.add_spacer(width=60,location=(0,-1))
        # Signals
        @controller.exsafe
        def setup_subtraction():
            enabled=self.v["enabled"]
            method=self.v["method"]
            if method=="snapshot":
                self.image_processor.csi.setup_snapshot_saving(self.v["background_saving"])
                self.image_processor.csi.setup_snapshot_subtraction(self.v["comb_count"],self.v["comb_mode"],self.v["comb_step"])
            else:
                self.image_processor.csi.setup_running_subtraction(self.v["comb_count"],self.v["comb_mode"],self.v["comb_step"])
            self.image_processor.csi.setup_subtraction_method(method=method,enabled=enabled)
            self.recv_parameters()
        for w in ["method","enabled","comb_count","comb_step","comb_mode","background_saving"]:
            self.params.vs[w].connect(setup_subtraction)
        self.params.vs["grab_background"].connect(lambda: self.image_processor.ca.grab_snapshot_background())
        # Timer
        self.add_timer_event("recv_parameters",self.recv_parameters,period=0.5)
        self.setEnabled(False)
        self.ctl.res_mgr.cs.add_resource("process_activity","processing/background",
            caption="Background subtraction",short_cap="Bg",order=1)


    @controller.exsafe
    def recv_parameters(self):
        """Update frame processing indicators (snapshot background mode and count)"""
        if self.image_processor.v["overridden"]:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            method=self.v["method"]
            is_snapshot=method=="snapshot"
            self.params.set_enabled(["grab_background","background_state"],is_snapshot)
            self.params.set_enabled(["background_saving"],is_snapshot and self.v["enabled"])
            self.i["comb_count"]="{} / {}".format(self.image_processor.v[method,"grabbed"],self.image_processor.v[method,"parameters/count"])
            bg_state=self.image_processor.v["snapshot/background/state"]
            self.v["background_state"]={"none":"Not acquired","acquiring":"Accumulating","valid":"Valid","wrong_size":"Wrong size"}[bg_state]
            enabled=False
            if self.image_processor.v["enabled"]:
                method=self.image_processor.v["method"]
                if method=="snapshot":
                    enabled=self.image_processor.v["snapshot/background/state"]=="valid"
                elif method=="running":
                    enabled=self.image_processor.v["running/background/frame"] is not None
            self.ctl.call_thread_method("update_activity_status","processing","background",status="on" if enabled else "off")