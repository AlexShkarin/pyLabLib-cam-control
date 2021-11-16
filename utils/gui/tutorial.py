from pylablib.core.gui.widgets import param_table
from pylablib.core.gui import QtCore, utils
from pylablib.core.thread.controller import exsafe
from pylablib.gui.widgets import highlighter


class TutorialBox(param_table.ParamTable):
    """
    Tutorial window.

    Displays navigation and text, and highlights corresponding GUI elements.
    """
    def setup(self, main_frame):
        super().setup("tutorial_box",add_indicator=False)
        self.setWindowTitle("Tutorial")
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.add_text_label("caption",location=(0,0,1,3))
        self.w["caption"].setStyleSheet("font: bold")
        self.add_text_label("hint",location=(1,1,1,3))
        self.w["hint"].setWordWrap(True)
        self.w["hint"].setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.w["hint"].setOpenExternalLinks(True)
        with self.using_new_sublayout("buttons","grid"):
            self.add_button("prevst",caption="<",location=(0,0,1,1))
            self.add_button("nextst",caption=">",location=(0,1,1,1))
            self.add_button("prevch",caption="<<",location=(1,0,1,1))
            self.add_button("nextch",caption=">>",location=(1,1,1,1))
            for n in ["prevst","nextst","prevch","nextch"]:
                policy=self.w[n].sizePolicy()
                policy.setRetainSizeWhenHidden(True)
                self.w[n].setSizePolicy(policy)
        self.vs["prevch"].connect(exsafe(lambda: self.select_stage(self._prev_chapter(self.stage[0]))))
        self.vs["nextch"].connect(exsafe(lambda: self.select_stage(self._next_chapter(self.stage[0]))))
        self.vs["prevst"].connect(exsafe(lambda: self.select_stage(*self._prev_stage(*self.stage))))
        self.vs["nextst"].connect(exsafe(lambda: self.select_stage(*self._next_stage(*self.stage))))
        self.set_row_stretch(1,1)
        self.setFixedSize(400,150)
        self.main_frame=main_frame
        self.main_frame.closed.connect(self.close)
        self.hframe=highlighter.QHighlightFrame(self.main_frame)
        self.hframe.setup(border=5,style="background: rgba(156,204,101,128)")

        self.filter_plugin="filter.filt"
        self.trigsave_plugin="trigger_save.trigsave"
        self.all_stages=self.get_all_stages()
        self.all_chapters=list(self.all_stages)
        self.select_stage(self.all_chapters[0])
    
    def closeEvent(self, event):
        if self.hframe is not None:
            self.hframe.remove_all_anchors()
            utils.delete_widget(self.hframe)
            self.hframe=None
        return super().closeEvent(event)
    def _prev_chapter(self, chapter):
        chidx=self.all_chapters.index(chapter)
        return self.all_chapters[chidx-1] if chidx>0 else None
    def _next_chapter(self, chapter):
        chidx=self.all_chapters.index(chapter)
        return self.all_chapters[chidx+1] if chidx<len(self.all_chapters)-1 else None
    def _prev_stage(self, chapter, stage):
        stidx=self.all_stages[chapter].index(stage)
        if stidx==0:
            prevch=self._prev_chapter(chapter)
            return (None,None) if prevch is None else (prevch,self.all_stages[prevch][-1])
        return chapter,self.all_stages[chapter][stidx-1]
    def _next_stage(self, chapter, stage):
        stidx=self.all_stages[chapter].index(stage)
        if stidx==len(self.all_stages[chapter])-1:
            nextch=self._next_chapter(chapter)
            return (None,None) if nextch is None else (nextch,self.all_stages[nextch][0])
        return chapter,self.all_stages[chapter][stidx+1]
    def setup_display(self, chapter, stage):
        """Setup text and navigation based on the current chapter and stage"""
        prevch=self._prev_chapter(chapter)
        nextch=self._next_chapter(chapter)
        prevstch,prevst=self._prev_stage(chapter,stage)
        nextstch,nextst=self._next_stage(chapter,stage)
        self.v["caption"]="   {} / {}".format(*self.get_stage(chapter,stage)[0][:2])
        self.v["hint"]=self.get_stage(chapter,stage)[0][-1]
        self.w["prevch"].setText("<<" if prevch is None else "<<  {}".format(self.get_stage(prevch)[0][0]))
        self.set_visible("prevch",prevch is not None)
        self.w["nextch"].setText(">>" if nextch is None else "{}  >>".format(self.get_stage(nextch)[0][0]))
        self.set_visible("nextch",nextch is not None)
        prevst_label=None if prevst is None else (self.get_stage(chapter,prevst)[0][1] if prevstch==chapter else "{} / {}".format(*self.get_stage(prevstch,prevst)[0][:2]))
        self.w["prevst"].setText("<" if prevst is None else "<  {}".format(prevst_label))
        self.set_visible("prevst",prevst is not None)
        nextst_label=None if nextst is None else (self.get_stage(chapter,nextst)[0][1] if nextstch==chapter else "{} / {}".format(*self.get_stage(nextstch,nextst)[0][:2]))
        self.w["nextst"].setText(">" if nextst is None else "{}  >".format(nextst_label))
        self.set_visible("nextst",nextst is not None)
    def add_layout_anchors(self, container, anchors):
        self.hframe.remove_all_anchors()
        for a in anchors:
            if isinstance(a,tuple) and a[0] in ["e","r"]:
                k,a=a
            else:
                k="r"
            self.hframe.add_layout_anchor(container,a,kind="row" if k=="r" else "element")
        self.hframe.refresh()
    def select_stage(self, chapter, stage=None):
        """Select given chapter and stage (``None`` means the first stage)"""
        if stage is None:
            stage=self.all_stages[chapter][0]
        self.setup_display(chapter,stage)
        cont,anchors=self.get_stage(chapter,stage,show=True)[1]
        self.add_layout_anchors(cont,anchors)
        self.stage=chapter,stage
    


    def get_all_stages(self):
        """Get dictionary ``{chapter: [stages]}`` of all chapters and stages"""
        stages={
            "intro":["overview","navigation","further_info"],
            "camera":["overview","acquisition","connection","parameters"],
            "cam_status":["overview","name","connection","acquisition","frame_counters","buffer_status","fps"],
            "images":["overview","overview_image","overview_control","transflip","levels","normalize","histogram","color_scheme","lines","linecuts","updating"],
            "saving":["overview","standard","saving","path","path_modifiers","format","batch_size","filesplit","pretrigger_buffer","save_settings","event_log",
                        "snapshot","snap","snapshot_path","snapshot_use_main_path","snapshot_source","snapshot_format"],
            "save_status":["overview","saving_process","saving_process_cont","received","saved","missed","status_line","saving_buffer","pretrigger"],
            "processing":["overview","indicator","preproc/overview","preproc/spatial","preproc/temporal","preproc/dtype","preproc/enable",
                        "bgsub/overview","bgsub/method","bgsub/method_snapshot","bgsub/method_running","bgsub/comb_mode","bgsub/grab","bgsub/save","bgsub/enable",
                        "slowdown/overview","slowdown/source_fps","slowdown/slowdown_fps","slowdown/slowdown_buffer","slowdown/enable"]
        }
        if (self.filter_plugin,"__controller__") in self.main_frame.c:
            stages["filters"]=["overview","general","loading","selection","current_filter","enable","description","filter_parameters","plot"]
        if (self.trigsave_plugin,"__controller__") in self.main_frame.c:
            stages["trigsave"]=["overview","save_mode","limit_videos","trigger_mode","save_period","trigger_source","trigger_threshold","dead_time","enable"]
        return stages
    def get_stage(self, chapter, stage=None, show=False):
        """
        Get stage information.

        If ``show==True``, show the highlighted element (e.g., by changing tabs).
        Return tuple ``(text, gui)``, where ``text`` is a tuple ``(chapter, stage, description)``,
        and ``gui`` is a tuple ``(container, anchors)`` (used for highlighting).
        """
        ch=None
        cont=None
        stages={}
        if chapter=="intro":
            ch="Tutorial"
            cont=self.main_frame
            stages={
                "overview": ("Overview",
                    ("This is a short <b>tutorial</b> which highlights the main parts of the software. You can quit it at any time by closing this window, "
                    "and you can restart it later from the <i>Extras</i>  menu in the lower right corner."),
                        [("e","extras")]),
                "navigation": ("Navigation",
                    ("The buttons below help you <b>navigate</b> the tutorial. The top two buttons move between different highlights, "
                    "while the bottom buttons move between larger chapters dealing with separate parts of the interface."),
                        []),
                "further_info": ("Further information",
                    ("You can find a much more detailed information about this software in its manual "
                    "<a href='https://pylablib-cam-control.readthedocs.io/'>online</a> or in the <i>docs</i>  folder."),
                        [])
            }
        if chapter=="camera":
            ch="Camera"
            if show:
                self.main_frame.control_tabs.set_by_name("cam_tab")
            cont=self.main_frame.c["cam_controller/settings"]
            stages={
                "overview": ("Overview",
                    "This part controls the <b>camera</b>.",
                        [cont.parent()]),
                "acquisition": ("Acquisition",
                    "These buttons <b>start and stop acquisition</b>. By default, it is not running, so you need to press <i>Start acquisition</i>  first.",
                        ["start","stop"]),
                "connection": ("Connection",
                    "These buttons let you <b>disconnect</b> the camera to use in a different application and then <b>connect</b> it later.",
                        ["connect","disconnect"]),
                "parameters": ("Parameters",
                    "Here specific <b>camera parameters</b> are controlled.",
                        [cont.c["settings_tabs"]]),
            }
        if chapter=="cam_status":
            ch="Camera status"
            if show and self.main_frame.compact_interface:
                self.main_frame.control_tabs.set_by_name("cam_tab")
            cont=self.main_frame.c["cam_controller/camstat"]
            stages={
                "overview": ("Overview",
                    "This is the <b>camera status</b> panel. It displays the camera name, connection, and, most importantly, its buffer fill status.",
                        [cont]),
                "name": ("Camera name and kind",
                    "This is the <b>camera name and kind</b>. Camera name is built automatically based on its model and serial number.",
                        ["cam_name","cam_kind"]),
                "connection": ("Connection",
                    ("Here is the <b>connection status</b>. Normally it should always read <i>Connected</i>. "
                    "The only cases when the camera is disconnected is when it could not be connected on the start, or if you explicitly used the <i>Disconnect</i>  button."),
                        ["connection"]),
                "acquisition": ("Acquisition",
                    ("Here is the <b>acquisition status</b>, which shows whether the camera is acquiring. It can also show "
                    "<i>Setting up..</i>  or <i>Cleaning up...</i>  if the acquisition setup takes some time.<br> "
                    "Note that if the camera is in the external trigger mode but no trigger is supplied, it can be in the acquiring state without generating any frames."),
                        ["acquisition"]),
                "frame_counters": ("Frame counters",
                    ("This is the <b>number of acquired and read out frames</b>. Ideally these number should be the same, "
                    "and any discrepancy means that some frames were lost in transfer. You can consult "
                    "<a href='https://pylablib-cam-control.readthedocs.io/en/latest/troubleshooting.html'>troubleshooting</a> for details."),
                        ["frames/acquired","frames/read"]),
                "buffer_status": ("Buffer status",
                    ("This is the <b>buffer status</b> showing the fill level of the camera frame buffer. If the buffer is almost completely full or the fill level is steadily increasing, "
                    "it means that the software can not deal with the frame or data rate, and you need to reduce it (decrease frame rate or frame size) "
                    "or reduce the CPU load (turn off filters, background subtraction, etc.)"),
                        ["frames/buffstat"]),
                "fps": ("FPS",
                    "Here you can see a rough estimate of the <b>camera frame rate</b>.",
                        ["frames/fps"]),
            }
        if chapter=="images":
            ch="Image display"
            if show:
                self.main_frame.plots_tabs.set_by_name("standard_frame")
            cont=self.main_frame.c["cam_controller/plotter_ctl/params"]
            stages={
                "overview": ("Overview",
                    "Here is the <b>image display</b> section. Depending on the installed plugins, more than one image display tab can be present (e.g., for filters).",
                        [self.main_frame.c["cam_controller/plotter_ctl"].parent().parent()]),
                "overview_image": ("Image display",
                    ("This is the main <b>image display</b>, which displays the image and (if enabled) the image histogram on the left "
                    "and the linecut plots on the bottom."),
                        [self.main_frame.c["cam_controller/plotter_area"]]),
                "overview_control": ("Display control",
                    "This panel controls the <b>image display</b>. These parameters only affect the frames display, and <b>do not change the way data is saved</b>.",
                        [self.main_frame.c["cam_controller/plotter_ctl"].parent()]),
                "transflip": ("Flips and rotations",
                    "With these checkboxes you can control the image <b>orientation</b>.",
                        ["flip_x","flip_y","transpose"]),
                "levels": ("Levels",
                    "Here you can change the image <b>levels</b>, which control the display color scale.",
                        ["minlim","maxlim"]),
                "normalize": ("Autoscale",
                    "Alternatively, you can choose to <b>autoscale</b> the image levels.",
                        ["normalize"]),
                "histogram": ("Histogram",
                    "Here you can enable or disable the <b>histogram histogram</b>, which shows the distribution of the image values and the selected color range.",
                        ["show_histogram","auto_histogram_range"]),
                "color_scheme": ("Color scheme",
                    "You can also change the <b>color scheme</b> by right-clicking on the <i>color bar</i>  or dragging or changing color on the markers.",
                        ["show_histogram","auto_histogram_range"]),
                "lines": ("Lines",
                    ("Here you can enable a pair of <b>lines</b> in the image. You can move them either by dragging, or by entering their coordinates in the boxes. "
                    "<i>Center lines</i>  button recenters the lines within the image."),
                        ["show_lines","hlinepos","vlinepos","center_lines"]),
                "linecuts": ("Line cuts",
                    ("You can also enable plotting <b>line cuts</b> for the enabled lines. "
                    "If <i>Line cut width</i>  is above 1, the line cuts are calculated by averaging several consecutive cuts together.<br> "
                    "Note that plotting line cuts is relatively computation-intensive, so you should turn them off if the operation becomes laggy."),
                        ["show_linecuts","linecut_width"]),
                "updating": ("Updating",
                    ("This button enables or disable the <b>plot updating</b>. "
                    "Disabling saves computational time, which can help if the operation is slow or the software can not sustain high frame rate."),
                        ["update_image"]),
            }
        if chapter=="saving":
            ch="Saving control"
            if show and self.main_frame.compact_interface:
                self.main_frame.control_tabs.set_by_name("save_tab")
            cont=self.main_frame.c["cam_controller/savebox/params"]
            stages={
                "overview": ("Overview",
                    ("Here is the <b>saving control</b> section. It determines where and in which format the data is saved, whether pretrigger is used, "
                    "and also controls the additional event log."),
                        [self.main_frame.c["cam_controller/savebox"]]),
                "standard": ("Standard streaming",
                    "The top part controls the standard <b>data streaming</b>. This mode continuously saves all of the frames from the camera with minimal alterations.",
                        [0,"log_event"]),
                "saving": ("Saving button",
                    "This is the main button which <b>starts or stops data streaming</b>. In addition, if frame <i>Limit</i>  is enabled, \
                        the streaming can stop automatically after a given number of frames.",
                        [("e","saving")]),
                "path": ("Base save path",
                    ("Here you enter the <b>save path</b>. The default extension is added if missing. If the containing folder does not exist, "
                    "it is created automatically."),
                        ["path","browse"]),
                "path_modifiers": ("Path modification",
                    ("These checkboxes <b>modify the save path</b> for more convenient data organization.<br> "
                    "<i>Separate folder</i>  creates a separate folder for each new dataset, and <i>Add date/time</i>  "
                    "automatically appends current date and time to the entered base path to avoid duplicate file names."),
                        ["make_folder","add_datetime"]),
                "duplicate_name": ("Duplicate name behavior",
                    ("Here you can choose what happens when <b>saving to an existing location</b>. You can choose to either rename the new path to avoid name conflict, "
                    "overwrite the old data, or append to it (it still results in a partial overwrite, so generally not recommended)."),
                        ["on_name_conflict"]),
                "format": ("File format",
                    ("This is the <b>storage format</b>. Currently you can choose raw binary, Tiff, or Big Tiff (unlike Tiff it handles files larger than 2Gb, "
                    "but is not as widely supported)."),
                        ["format"]),
                "batch_size": ("Dataset size",
                    ("Here you can <b>limit the number of frames per dataset</b>. By default, the streaming is continuous until manually stopped, "
                    "but if you want to save a defined number of frames, you can activate the <i>Limit</i>  button and specify the limit."),
                        ["batch_size"]),
                "filesplit": ("File splitting",
                    ("This lets you <b>split the frames into several files</b>. This is useful for very large datasets, where having a single "
                    "giant file would be inconvenient. It is also necessary to save more than 2Gb into a Tiff format, since it does not support files larger than that."),
                        ["filesplit"]),
                "pretrigger_buffer": ("Pretrigger buffer",
                    ("Here you can control the <b>pretrigger buffer</b> parameters. If enabled, it always keeps in RAM a given number of previous frames, "
                    "and stores them when the saving is started. This effectively lets you start saving data before you press <i>Saving</i>  button, "
                    "which is useful for recording of rare or fast events."),
                        ["pretrigger_size","pretrigger_clear"]),
                "save_settings": ("Settings saving",
                    ("This checkbox controls whether <b>additional settings file</b> is stored with the data. This file includes comprehensive camera status, "
                    "GUI state, and detailed stored data description. It is highly recommended to always store it."),
                        [("e","save_settings")]),
                "event_log": ("Event log",
                    ("Here you can <b>generate an event log</b>. This is a separate text file, which records the entered message together with its time and frame index "
                    "whenever you press <i>Log event</i>  button."),
                        ["event_msg","log_event"]),
                "snapshot": ("Snapshot saving",
                    ("In addition to streaming raw camera data, you can also <b>save snapshots of displayed images</b>. It saves the images exactly as displayed "
                    "including all of the processing, e.g., background subtraction or filters. However, it only saves a single image."),
                        [("snap_header",0),"snap_format"]),
                "snap": ("Snap button",
                    "This button takes the snapshot. Unlike the <i>Saving</i>  button which start or stops streaming, <i>Snap</i>  immediately saves a single frame.",
                        [("e","snap_displayed")]),
                "snapshot_path": ("Snapshot save path",
                    "These controls determine the <b>snapshot save path</b>. Their meaning is exactly the same as the corresponding streaming settings.",
                        ["snap_path","snap_add_datetime"]),
                "snapshot_use_main_path": ("Snapshot save path",
                    "Alternatively, you can choose to <b>use the main streaming path</b>. In this case, the snapshot path will simply add <i>_snapshot</i>  suffix to it.",
                        [("e","default_snap_path")]),
                "snapshot_source": ("Snapshot source",
                    "In case there are several image display tabs, here you can <b>choose the image display to save</b>.",
                        [("e","snap_display_source")]),
                "snapshot_format": ("Snapshot format",
                    "Similarly to the streaming, you can choose between raw binary and Tiff formats.",
                        [("e","snap_format")]),
            }
        if chapter=="save_status":
            ch="Saving status"
            if show and self.main_frame.compact_interface:
                self.main_frame.control_tabs.set_by_name("save_tab")
            cont=self.main_frame.c["cam_controller/savestat"]
            stages={
                "overview": ("Overview",
                    "This is the <b>save status</b> panel. It displays the number of received, saved, and missed frames, and the pretrigger status.",
                        [cont]),
                "saving_process": ("Saving process",
                    ("The frames to be saved are first sent to the <b>saving buffer</b>, from which the data is saved to the drive. "
                    "If the drive speed is larger than the camera data rate, then the frames are saved immediately, and the buffer stays empty. "
                    "In this case, saving can continue indfinitely."),
                        [cont]),
                "saving_process_cont": ("Saving process",
                    ("If the camera data rate is larger than the drive rate, the buffer gets gradually filled. Once it gets overfilled, the data can be lost. "
                    "If there frames in the buffer by the time saving is done (either manually, or upon receiving the specified number of frames), "
                    "writing to the drive will continue until the buffer is empty. If the new saving is started in the meantime, these frames will be lost."),
                        [cont]),
                "received": ("Received frames",
                    ("This is the <b>number of frames received and scheduled for saving</b>. These show how many frames have been received from the camera to be saved, "
                    "and how many of these are scheduled for saving. Ideally these two are the same, and they are only different if the frames are lost or if "
                    "the saving buffer is overfilled."),
                        ["frames/received","frames/scheduled"]),
                "saved": ("Saved frames",
                    ("This is the <b>number of already saved frames</b>. It can be smaller than the scheduled frames, which means that some frames still wait in "
                    "the saving buffer to be stored to the disk."),
                        ["frames/saved"]),
                "missed": ("Missed frames",
                    "Finally, this is the <b>number of missed frames</b>. It combines both frames missed from the camera readout, and frames skipped during saving.",
                        ["frames/missed"]),
                "status_line": ("Status line",
                    "Some cameras (e.g., Photon Focus) support status <b>line within the frame</b>. It provides a more robust check of missing frames, and the results are shown here.",
                        ["frames/status_line_check"]),
                "saving_buffer": ("Saving buffer",
                    ("This is the <b>saving buffer status</b> showing the current and the maximal size of this buffer. "
                    "As long as it is not completely full, everything is fine, and no frames are lost. "
                    "You can find more details in the <a href='https://pylablib-cam-control.readthedocs.io/en/latest/pipeline.html#saving-buffer'>documentation</a>."),
                        ["frames/ram_status"]),
                "pretrigger": ("Pretrigger buffer",
                    ("This is the <b>pretrigger buffer status</b>. "
                    "The first two lines show its fill status in frames and in RAM size. In order to function properly, it should be completely filled. "
                    "The last line shows the number of skipped within the buffer; like with other such counters, ideally it should be zero."),
                        ["frames/pretrigger_frames","frames/pretrigger_skipped","frames/pretrigger_ram"]),
            }
        if chapter=="processing":
            ch="On-line processing"
            if show:
                if stage=="indicator":
                    self.main_frame.plots_tabs.set_by_name("standard_frame")
                else:
                    self.main_frame.control_tabs.set_by_name("proc_tab")
            if stage in {None,"overview"}:
                cont=self.main_frame.c["control_tabs/proc_tab"]
            elif stage=="indicator":
                cont=self.main_frame.c["plot_tabs/standard_frame/processing_indicator"]
            elif stage.startswith("preproc"):
                cont=self.main_frame.c["control_tabs/proc_tab/frame_preprocessing"]
            elif stage.startswith("bgsub"):
                cont=self.main_frame.c["control_tabs/proc_tab/frame_processing"]
            elif stage.startswith("slowdown"):
                cont=self.main_frame.c["control_tabs/proc_tab/slowdown"]
            stages={
                "overview": ("Overview",
                    "This is the <b>basic online processing</b> control.",
                        ["frame_preprocessing","frame_processing","slowdown"]),
                "indicator": ("Processing indicator",
                    "For convenience, the activated processing stages are <b>shown above the image display</b>.",
                        [cont]),
                "preproc/overview": ("Prebinning",
                    ("This is the <b>prebinning</b> control. Here you can enable spatial and temporal binning of frames before they are passed to later stages. "
                    "This is the only place which affects the saved frames."),
                        [cont]),
                "preproc/spatial": ("Prebinning / Spatial",
                    ("Here you control the <b>spatial binning</b>. It operates similar to the camera binning by combining several pixels in a square into a single pixel, "
                    "but since it works in post-processing, it is less effective. On the other hand, it gives more combination options, such as skipping (subsampling), min, and max."),
                        ["spat_bin_mode","spat_bin_x","spat_bin_y"]),
                "preproc/temporal": ("Prebinning / Temporal",
                    ("Here you control the <b>temporal binning</b>. It has the same combination options as the spatial, but combines several frames instead of several pixels within a frame. "
                    "Its effect is somewhat similar to increasing exposure time, but it does not suffer from the camera saturation, since the addition is done in post-processing."),
                        ["time_bin_mode","time_bin"]),
                "preproc/dtype": ("Prebinning / Frame data type",
                    ("With this checkbox you can <b>change the resulting frame type</b>. If unchecked, the result has the same type "
                    "as the original camera frame (usually an integer), which can affect the binning results due to rounding or integer overflows. Converting into float increases the "
                    "result precision, but the data takes 4 times more space."),
                        ["convert_to_float"]),
                "preproc/enable": ("Prebinning / Enable",
                    "Finally, here you can <b>enable or disable prebinning</b>.",
                        ["bin_enabled"]),
                "bgsub/overview": ("Background subtraction",
                    "This is the basic <b>background subtraction</b> control. It is only applied the displayed frame, and has no effect on the saved data.",
                        [cont]),
                "bgsub/method": ("Background subtraction / Method",
                    "First, you can select the <b>background calculation method</b>. There are two different modes: snapshot and running.",
                        ["method"]),
                "bgsub/method_snapshot": ("Background subtraction / Snapshot",
                    ("<b>Snapshot</b> accumulates several frames, combines them using the <i>mode</i>  below and stores as a single fixed background frame. "
                    "This method is appropriate when the background does not change with time."),
                        ["method"]),
                "bgsub/method_running": ("Background subtraction / Running",
                    ("<b>Running</b> works similarly, but instead combines frames immediately preceding the target frame. This effectively performs high-pass temporal filtering. "
                    "This method works better when the background is dynamic, but changes slower than the signal."),
                        ["method"]),
                "bgsub/comb_mode": ("Background subtraction / Combination",
                    ("Here you control <b>combination parameters</b>: number of frames to combine to get a background frame and the combination method. "
                    "Typically one uses either <i>Median</i>  or <i>Mean</i>; the first is more robust to outliers, but the second is much faster. "
                    "However, depending on the application, <i>Min</i>  can be more appropriate."),
                        ["comb_count","comb_mode"]),
                "bgsub/grab": ("Background subtraction / Grabbing",
                    ("If you use <i>Snapshot</i>  subtraction method, here you can <b>start grabbing the background</b>. As soon as this button is pressed, "
                    "the next <i>Frames count</i>  frames are grabbed and combined to form the background."),
                        ["grab_background"]),
                "bgsub/save": ("Background subtraction / Saving",
                    ("Since background subtraction does not affect the saved data, snapshot subtraction effect can be lost. "
                    "This option <b>enables saving of the background</b> along with the main data."),
                        ["background_saving"]),
                "bgsub/enable": ("Background subtraction / Enable",
                    "Finally, here you can <b>enable or disable background subtraction</b>.",
                        ["enabled"]),
                "slowdown/overview": ("Slowdown",
                    ("This is the <b>playback slowdown</b> control, which lets you temporarily reduce the display frame rate and slow down the camera feed to examine fast processes. "
                    "Similar to the background subtraction, it does not affect the data saving, which proceeds at the regular speed."),
                        [cont]),
                "slowdown/source_fps": ("Slowdown / Source FPS",
                    "Here you can see the <b>source FPS</b>, which should normally be equal to the camera frame rate divided by the temporal binning factor.",
                        ["source_fps"]),
                "slowdown/slowdown_fps": ("Slowdown / Target FPS",
                    "Here you set up the <b>target FPS</b>. The slowdown factor is then the ratio of the source to the target FPS.",
                        ["slowdown_fps"]),
                "slowdown/slowdown_buffer": ("Slowdown / Buffer size",
                    "Here you can control the <b>size of the slowdown buffer</b>. This size controls for how long the slowdown can continue.",
                        ["slowdown_buffer"]),
                "slowdown/enable": ("Slowdown / Enable",
                    "Finally, here you can <b>enable or disable slowdown</b>.",
                        ["slowdown_enabled"]),
            }
        if chapter=="filters":
            ch="Filters"
            cont=self.main_frame.c[self.filter_plugin,"__controller__/ctl_tab"]
            if show:
                self.main_frame.control_tabs.set_by_name((self.filter_plugin,"ctl_tab"))
                if stage in ["current_filter","description","filter_parameters"]:
                    if getattr(cont,"current_filter",None) is None:
                        cont.v["load_filter"]=True
            stages={
                "overview": ("Overview",
                    "This is the <b>image filters</b> tab. It lets you load different built-in or custom filters and change their parameters.",
                        [cont]),
                "general": ("General controls",
                    "The top part <b>controls which filter is selected</b>.",
                        ["params"]),
                "loading": ("Loading and unloading",
                    ("Here you <b>select the filter and load it</b>. When a new filter is loaded, the current one is automatically unloaded and all its accumulated information is cleared. "
                    "You can also <i>Load</i>  the same filter to effectively reload it to, e.g., reset the accumulated buffers."),
                        ["params/filter_id","params/load_filter","params/unload_filter"]),
                "selection": ("Custom filters",
                    ("If you add <b>custom-designed filters</b>, they will automatically show up in the selection. The process of adding custom filters is described in the "
                    "<a href='https://pylablib-cam-control.readthedocs.io/en/latest/expanding.html#custom-filters'>documentations</a>."),
                        ["params/filter_id","params/load_filter","params/unload_filter"]),
                "current_filter": ("Current filter",
                    "Here you can see <b>the name of the current filter</b>.",
                        ["params/loaded_filter"]),
                "enable": ("Enable",
                    "This button lets you <b>enable or disable the filter</b>. This is useful to save computational resources, or to quickly compare raw and filtered images.",
                        ["params/enabled"]),
                "description": ("Description",
                    "Below there is <b>detailed filter description</b> provided by the filter's author.",
                        ["params/description"]),
                "filter_parameters": ("Filter parameters",
                    "Finally, in the bottom you can change <b>specific filter parameters</b>. These parameters depend on the filter and are also defined by its author.",
                        ["filter_params"]),
                "plot": ("Filter display",
                    "The filters results in plotted in its own separate tab. Similar to the standard tab, above you can see a brief description of the processing steps applied to the image.",
                        [self.main_frame.c[self.filter_plugin,"__controller__/plt_tab"]]),
            }
        if chapter=="trigsave":
            ch="Saving trigger"
            if show:
                self.main_frame.control_tabs.set_by_name("plugins")
            cont=self.main_frame.c[self.trigsave_plugin,"__controller__/params"]
            stages={
                "overview": ("Overview",
                    "This is the <b>saving trigger</b> plugin. It can automate data acquisition either on timer, or based on the image.",
                        [cont.parent()]),
                "save_mode": ("Save mode",
                    ("First you select the <b>save mode</b>. It can either be a single snap save, or a full dataset streaming. "
                    "Note that if you use the full mode, in most cases it makes sense to limit the number of frames per dataset."),
                        ["save_mode"]),
                "limit_videos": ("Limit",
                    ("Next, you can choose to <b>limit the number of saved videos</b>. If enabled, it stops the automation after the given number of snaps or datasets "
                    "has been saved. Otherwise, the process continues until stopped manually."),
                        ["limit_videos","max_videos"]),
                "trigger_mode": ("Trigger mode",
                    ("After that, you choose the <b>trigger mode</b>. It can be either on timer, or image-based. "
                    "In the first case saving is simply triggered with a given periodicity. In the second it is started whenever a maximal image value goes above a certain threshold."),
                        ["trigger_mode"]),
                "save_period": ("Save period",
                    "If use the timer mode, the only available parameter is the <b>save period</b>.",
                        ["period"]),
                "trigger_source": ("Image trigger source",
                    ("In the trigger mode, first you define the <b>trigger image source</b>. Usually it is either the standard image (possibly with background subtraction), "
                    "or a filter result. The second method is usually more powerful, since it lets you define custom filter to highlight frames of interest for triggering."),
                        ["frame_source"]),
                "trigger_threshold": ("Image trigger threshold",
                    "Next, you define the <b>trigger threshold</b>. In any pixel of the source image has a value above this threshold, the saving is triggered.",
                        ["image_trigger_threshold"]),
                "dead_time": ("Dead time",
                    ("In addition, you can also define the <b>dead time</b> for this trigger. Typically when image trigger is used, several consecutive images can trigger saving. "
                    "To avoid multiple triggers, you can define the dead time, which is the time after the trigger during which new triggers are ignored. "
                    "Usually you want this time to be at least as large as the length of your dataset."),
                        ["dead_time"]),
                "enable": ("Enable",
                    "Finally this button lets you <b>start or stop the saving trigger routine</b>.",
                        ["enabled"]),
            }
        name,text,anchors=stages.get(stage,(None,None,[]))
        return (ch,name,text),(cont,anchors)