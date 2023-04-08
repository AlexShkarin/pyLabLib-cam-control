from pylablib.core.gui.widgets import container, param_table
from pylablib.core.thread import controller



class PlotControl_GUI(container.QGroupBoxContainer):
    """
    Time series plot controller widget.

    Controls time series calculation, ROI, and memory size..
    """
    def setup(self, channel_accumulator_thread, plot_window, settings=None):
        super().setup(caption="Time series plot",no_margins=True)
        # Setup threads
        self.channel_accumulator_thread=channel_accumulator_thread
        self.settings=settings or {}
        self.channel_accumulator=controller.sync_controller(self.channel_accumulator_thread)

        # Setup plot window
        self.plot_window=plot_window
        self.plot_window.setLabel("left","Signal")
        self.plot_window.showGrid(True,True,0.7)
        self.plot_lines={}
        self.plot_markers={}
        # Setup control table
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup(add_indicator=False)
        self.params.add_toggle_button("enable","Enable").get_value_changed_signal().connect(self.enable)
        self.params.add_combo_box("source",options=["Display frame mean","Raw frame mean"],index_values=["show","raw"],label="Source")
        self.params.vs["source"].connect(self.change_source)
        self.params.add_num_edit("skip_count",1,limiter=(1,None,"coerce","int"),formatter=("int"),label="Calculate every: ")
        self.params.add_check_box("roi/enable","Use ROI").get_value_changed_signal().connect(self.setup_roi)
        with self.params.using_new_sublayout("roi","grid"):
            self.params.add_num_edit("roi/center/x",value=0,limiter=(0,None,"coerce","int"),formatter="int",label="Center: ")
            self.params.add_num_edit("roi/center/y",value=0,limiter=(0,None,"coerce","int"),formatter="int",location=(-1,2))
            self.params.add_num_edit("roi/size/x",value=0,limiter=(1,None,"coerce","int"),formatter="int",label="Size: ")
            self.params.add_num_edit("roi/size/y",value=0,limiter=(1,None,"coerce","int"),formatter="int",location=(-1,2))
        self.params.add_button("roi/reset","Reset ROI").get_value_changed_signal().connect(self.reset_roi)
        for n in ["center/x","center/y","size/x","size/y"]:
            self.params.w["roi/"+n].setMaximumWidth(60)
            self.params.vs["roi/"+n].connect(self.setup_roi)
        self.params.add_spacer(10)
        self.params.add_toggle_button("update_plot","Update plot")
        self.params.add_num_edit("disp_last",1000,limiter=(1,None,"coerce","int"),formatter=("int"),label="Display last: ")
        self.params.add_button("reset_history","Reset history").get_value_changed_signal().connect(lambda: self.channel_accumulator.ca.reset())
        self.params.add_padding("horizontal",location=(0,"next"))
        self.params.layout().setColumnStretch(1,0)
        self.params.contained_value_changed.connect(self.setup_gui_state)
        self._update_roi_display((0,0),(0,0))
        self.setup_gui_state()
        self.params.vs["skip_count"].connect(self.setup_processing)
        self.enable(False)
        self.change_source("show")
        self.add_timer_event("update_plot",self.update_plot,period=0.1)

    @controller.exsafe
    def enable(self, enabled):
        """Enable time series accumulation and plotting"""
        self.plot_window.setVisible(enabled)
        self.channel_accumulator.ca.enable(enabled)
        self.channel_accumulator.ca.reset()
    @controller.exsafe
    def change_source(self, src):
        """Set the frames source and changed the plot display accordingly"""
        self.channel_accumulator.ca.select_source(src)
        if src=="show":
            self.plot_window.setLabel("bottom","Time")
        else:
            self.plot_window.setLabel("bottom","Frame index")
        self._setup_plot_channels(["mean"],["Mean intensity"])
    @controller.exsafeSlot()
    def setup_processing(self):
        self.channel_accumulator.ca.setup_processing(skip_count=self.v["skip_count"])
    @controller.exsafeSlot()
    def setup_gui_state(self):
        """Enable or disable controls based on which actions are enabled"""
        enabled=self.v["enable"]
        roi_enabled=self.v["roi/enable"]
        update_plot=self.v["update_plot"]
        raw_frame_source=self.v["source"]=="raw"
        self.params.set_enabled(["source","skip_count","roi/enable","update_plot","reset_history"],enabled)
        self.params.set_enabled("skip_count",enabled and raw_frame_source)
        self.params.set_enabled("roi/enable",enabled)
        self.params.set_enabled("disp_last",enabled and update_plot)
        for name in ["center/x","center/y","size/x","size/y","reset"]:
            self.params.set_enabled("roi/"+name,enabled and roi_enabled)
        if enabled and roi_enabled:
            self.ctl.send_multicast(tag="image_plotter/control",value=("rectangles/show","mean_plot_roi"))
        else:
            self.ctl.send_multicast(tag="image_plotter/control",value=("rectangles/hide","mean_plot_roi"))
    
    def _update_roi_display(self, center, size):
        self.ctl.send_multicast(tag="image_plotter/control",value=("rectangles/set",("mean_plot_roi",center,size)))
    @controller.exsafeSlot()
    def reset_roi(self):
        """Reset ROI to the whole image"""
        new_roi=self.channel_accumulator.cs.reset_roi()
        if new_roi is not None:
            self.v["roi/center/x"]=new_roi.center()[0]
            self.v["roi/center/y"]=new_roi.center()[1]
            self.v["roi/size/x"]=new_roi.size()[0]
            self.v["roi/size/y"]=new_roi.size()[1]
            self._update_roi_display(new_roi.center(),new_roi.size())
    @controller.exsafeSlot()
    def setup_roi(self):
        """Update ROI parameters"""
        center=self.v["roi/center/x"],self.v["roi/center/y"]
        size=self.v["roi/size/x"],self.v["roi/size/y"]
        enabled=self.v["roi/enable"]
        self.channel_accumulator.ca.setup_roi(center=center,size=size,enabled=enabled)
        self._update_roi_display(center,size)

    def _setup_plot_channels(self, channels=None, labels=None, enabled=None):
        """Setup plot channel names and labels"""
        channels=channels or []
        labels=labels or [None]*len(channels)
        enabled=enabled or [True]*len(channels)
        if self.plot_window.plotItem.legend:
            self.plot_window.plotItem.legend.scene().removeItem(self.plot_window.plotItem.legend)
            self.plot_window.plotItem.legend=None
        for ch in self.plot_lines:
            self.plot_window.removeItem(self.plot_lines[ch])
            self.plot_window.removeItem(self.plot_markers[ch])
        if labels and any([l is not None for l in labels]):
            self.plot_window.addLegend()
        self.plot_lines={}
        self.plot_markers={}
        mpl_colors=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#bcbd22','#17becf']
        for i,(ch,l,en) in enumerate(zip(channels,labels,enabled)):
            if ch not in self.plot_lines:
                if ch=="idx":
                    self.plot_window.setLabel("bottom",l or "")
                elif en:
                    col=mpl_colors[i%len(mpl_colors)]
                    self.plot_lines[ch]=self.plot_window.plot([],[],pen=col,name=l)
                    self.plot_markers[ch]=self.plot_window.plot([],[],symbolBrush=col,symbol="o",symbolSize=5,pxMode=True)

    @controller.exsafe
    def update_plot(self):
        """Update frame processing indicators"""
        if self.v["update_plot"]:
            channels=self.channel_accumulator.csi.get_data(maxlen=self.v["disp_last"])
            if channels:
                idx=channels["idx"]
                for ch in self.plot_lines:
                    if ch in channels:
                        data=channels[ch]
                        self.plot_lines[ch].setData(idx,data)
                        if len(idx)>0:
                            self.plot_markers[ch].setData([idx[-1]],[data[-1]])