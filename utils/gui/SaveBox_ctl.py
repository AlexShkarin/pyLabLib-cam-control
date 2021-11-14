from pylablib.core.thread import controller
from pylablib.core.gui.widgets import container, param_table
from pylablib.core.utils import files as file_utils, general

from pylablib.core.gui import QtWidgets

import os
import datetime
import re


##### Saving parameter tables #####

class SaveBox_GUI(container.QGroupBoxContainer):
    """
    Saving controller widget.
    """
    _ignore_set_values={"saving"}
    def setup(self, ctl):
        super().setup(caption="Saving",no_margins=True)
        self.cam_ctl=ctl
        self.setMaximumWidth(250)

        self.record_in_progress=False
        self.popup_on_missing_frames=self.cam_ctl.settings.get("interface/popup_on_missing_frames",True)
        
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup(add_indicator=False)
        # Setup saving settings
        default_path=os.path.expanduser("~\\Documents\\frames")
        with self.params.using_new_sublayout("save_path","hbox",location=("next",0,1,3)):
            self.params.add_text_edit("path",label="Path",value=default_path)
        @controller.exsafe
        def browse_path():
            path,_=QtWidgets.QFileDialog.getSaveFileName(self,"Save camera data...",directory=self.v["path"])
            if path:
                self.v["path"]=path
        self.params.add_button("browse","Browse...",location=("next",2,1,1))
        self.params.vs["browse"].connect(browse_path)
        with self.params.using_new_sublayout("path_checkboxes","hbox"):
            self.params.add_check_box("make_folder",caption="Separate folder")
            self.params.add_padding()
            self.params.add_check_box("add_datetime",caption="Add date/time")
        with self.params.using_new_sublayout("name_conflict","hbox",location=("next",0,1,3)):
            self.params.add_combo_box("on_name_conflict",label="On duplicate name: ",
                options=["Overwrite","Append","Rename"],index_values=["overwrite","append","rename"],value="rename")
        self.params.add_spacer(6)
        self.params.add_combo_box("format",label="Format",options=["Raw binary","TIFF","Big TIFF"],index_values=["raw","tiff","bigtiff"])
        self.params.add_num_edit("batch_size",1,label="Frames",formatter="int",limiter=(1,None,"coerce","int"),)
        self.params.add_toggle_button("limit_frames","Limit",location=(-1,2,1,1))
        self.params.vs["limit_frames"].connect(lambda v: self.params.set_enabled("batch_size",v))
        self.params.add_num_edit("filesplit",1,label="Filesplit",formatter="int",limiter=(1,None,"coerce","int"),)
        self.params.add_toggle_button("do_filesplit","Split",location=(-1,2,1,1))
        self.params.vs["do_filesplit"].connect(lambda v: self.params.set_enabled("filesplit",v))
        self.params.add_num_edit("pretrigger_size",1,label="Pretrigger",formatter="int",limiter=(1,None,"coerce","int"),)
        self.params.add_toggle_button("pretrigger_enabled","Enabled",location=(-1,2,1,1))
        @controller.exsafe
        def update_pretrigger():
            self.params.set_enabled("pretrigger_size",self.v["pretrigger_enabled"])
            self.cam_ctl.setup_pretrigger()
        self.params.vs["pretrigger_size"].connect(update_pretrigger)
        self.params.vs["pretrigger_enabled"].connect(update_pretrigger)
        self.params.add_button("pretrigger_clear","Clear pretrigger",location=("next",2,1,1))
        self.params.vs["pretrigger_clear"].connect(self.cam_ctl.clear_pretrigger)
        self.params.add_check_box("save_settings",value=True,caption="Save settings",location=(-1,0,1,2))
        self.params.add_toggle_button("saving","Saving",location=("next",0,1,3))
        self.params.vs["saving"].connect(lambda v: self.cam_ctl.toggle_saving(mode="full",start=v))
        self.params.add_decoration_label("Event log message:",location=("next",0,1,3))
        self.params.add_text_edit("event_msg",value="",location=("next",0,1,3))
        self.params.add_button("log_event","Log event",location=("next",1,1,1))
        self.params.vs["log_event"].connect(self.cam_ctl.write_event_log)
        self.params.add_spacer(5)
        with self.params.using_new_sublayout("snap_header","hbox"):
            self.params.add_decoration_label("Snapshot:")
            self.params.add_padding()
            self.params.add_check_box("default_snap_path","Use main path")
        with self.params.using_new_sublayout("snap_save_path","hbox"):
            self.params.add_text_edit("snap_path",label="Path",value=default_path,location=("next",0,1,3))
        @controller.exsafe
        def browse_snap_path():
            path,_=QtWidgets.QFileDialog.getSaveFileName(self,"Save snapshot...",directory=self.v["snap_path"])
            if path:
                self.v["snap_path"]=path
        self.params.add_button("snap_browse","Browse...",location=("next",2,1,1))
        self.params.vs["snap_browse"].connect(browse_snap_path)
        with self.params.using_new_sublayout("snap_path_checkboxes","hbox"):
            self.params.add_check_box("snap_make_folder",caption="Separate folder")
            self.params.add_padding()
            self.params.add_check_box("snap_add_datetime",caption="Add date/time")
        @controller.exsafe
        def update_snap_path():
            default_path=self.v["default_snap_path"]
            if default_path:
                path,ext=os.path.splitext(self.v["path"])
                if ext not in self._allowed_ext[self.v["format"]]:
                    path=path+ext
                self.v["snap_path"]=path+"_snapshot"
                self.v["snap_make_folder"]=self.v["make_folder"]
                self.v["snap_add_datetime"]=self.v["add_datetime"]
            self.params.set_enabled(["snap_path","snap_browse","snap_make_folder","snap_add_datetime"],not default_path)
        for p in ["path","format","make_folder","add_datetime","default_snap_path"]:
            self.params.vs[p].connect(update_snap_path)
        self.v["default_snap_path"]=True
        with self.params.using_new_sublayout("snap_saving","hbox",location=("next",0,1,3)):
            self.params.add_button("snap_displayed","Snap")
            self.params.w["snap_displayed"].setMinimumWidth(50)
            self.params.vs["snap_displayed"].connect(lambda v: self.cam_ctl.toggle_saving(mode="snap",source=self.v["snap_display_source"]))
            self.params.add_combo_box("snap_display_source",options=[])
            self.update_display_source_options(reset_value=True)
            self.cam_ctl.frames_sources_updates.connect(self.update_display_source_options)
            self.params.add_padding()
            self.params.add_decoration_label("as")
            self.params.add_combo_box("snap_format",options=["Raw binary","TIFF"],index_values=["raw","tiff"],value="tiff")
        self.setEnabled(False)

    # Build a dictionary of camera parameters from the controls
    _default_ext={"raw":".bin","cam":".cam","tiff":".tiff","bigtiff":".btf"}
    _allowed_ext={k:[e] for k,e in _default_ext.items()}
    _allowed_ext["tiff"].append(".tif")
    _path_gens={"pfx":"{date}_{name}","sfx":"{name}_{date}","folder":"{date}/{name}"}
    def _expand_name(self, name, idx=None, add_datetime=False, as_folder=False):
        if add_datetime:
            pathgen_kind="folder" if as_folder else "file"
            pathgen=self.cam_ctl.settings.get(("interface/datetime_path",pathgen_kind),"sfx")
            pathgen=self._path_gens.get(pathgen,pathgen)
            date=datetime.datetime.now().strftime(r"%Y%m%d_%H%M%S")
            name=pathgen.format(name=name,date=date)
            if idx is not None:
                name="{}_{:03d}".format(name,idx)
        elif idx is not None:
            name="{}{:03d}".format(name,idx)
        return name
    def _is_name_taken(self, path, ext, split=False, as_folder=False):
        if as_folder:
            return os.path.exists(os.path.join(path))
        folder,name=os.path.split(path)
        for sfx in ["settings.dat","frameinfo.dat","background.bin","eventlog.dat"]:
            if os.path.exists(os.path.join(folder,"{}_{}".format(name,sfx))):
                return True
        if split:
            file_filter=re.escape(name)+r"_\d+"+re.escape(ext)
            return bool(file_utils.list_dir(folder,file_filter=file_filter).files)
        else:
            return os.path.exists(os.path.join(folder,name+ext))
    def collect_parameters(self, mode="full", resolve_path=True):
        """
        Get saving parameters from the widget as a dictionary.

        Also formats the saving file name (extension, perfixes, additional index).
        `mode` can be either ``"full"`` (collect parameters for full saving), or ``"snap"`` (collect parameteres for snap saving)
        """
        params={}
        params["batch_size"]=self.v["batch_size"] if self.v["limit_frames"] else None
        params["format"]=self.v["snap_format" if mode=="snap" else "format"]
        if resolve_path:
            use_snap_parameters=(mode=="snap" and not self.v["default_snap_path"])
            add_datetime=self.v["snap_add_datetime" if use_snap_parameters else "add_datetime"]
            make_folder=self.v["snap_make_folder" if use_snap_parameters else "make_folder"]
            fext=self._default_ext[params["format"]]
            aext=self._allowed_ext[params["format"]]
            path_kind="snap_path" if mode=="snap" else "path"
            if make_folder:
                path=self.v[path_kind]
                ext=fext
            else:
                path,ext=os.path.splitext(self.v[path_kind])
                if ext not in aext:
                    path+=ext
                    ext=fext
            folder,name=os.path.split(path)
            if mode=="snap" or self.v["on_name_conflict"]=="rename":
                idx=None
                iname=self._expand_name(name,idx,add_datetime=add_datetime,as_folder=make_folder)
                split=self.v["do_filesplit"]
                while self._is_name_taken(os.path.join(folder,iname),ext,split=split,as_folder=make_folder):
                    idx=0 if idx is None else idx+1
                    iname=self._expand_name(name,idx,add_datetime=add_datetime,as_folder=make_folder)
                name=iname
            else:
                name=self._expand_name(name)
            params["path"]=os.path.join(folder,name+ext)
            if not file_utils.is_path_valid(params["path"]):
                if not self.cam_ctl.no_popup:
                    QtWidgets.QMessageBox.warning(self,"Invalid path","Invalid path: {}".format(params["path"]),QtWidgets.QMessageBox.Ok)
                self.v["saving"]=False
                params["path"]=None
            params["path_kind"]="folder" if make_folder else "pfx"
        params["filesplit"]=self.v["filesplit"] if self.v["do_filesplit"] else None
        for p in ["pretrigger_size","pretrigger_enabled","save_settings","event_msg","snap_display_source"]:
            params[p]=self.v[p]
        params["append"]=self.v["on_name_conflict"]=="append" and mode=="full"
        return params
    # Update the interface indicators according to camera parameters
    def show_parameters(self, params):
        """
        Show saving parameters.

        Also deals with enabling/disabling controls during saving, and showing popups on missing frames.
        """
        self.setEnabled(True)
        record_in_progress=params.get("status/saving","stopped")=="in_progress"
        just_stopped=self.record_in_progress and not record_in_progress
        self.record_in_progress=record_in_progress
        if just_stopped: # record just stopped
            if self.popup_on_missing_frames and not self.cam_ctl.no_popup:
                if params.get("frames/missed",0)>0 or params.get("frames/status_line_check","na") not in {"na","off","none","ok"}:
                    QtWidgets.QMessageBox.warning(self,"Problems with frames","Some frames are missing, duplicated, or out of order",QtWidgets.QMessageBox.Ok)
            self.v["saving"]=False
        block_on_record=["path","browse","add_datetime","make_folder","on_name_conflict","format","limit_frames","do_filesplit","pretrigger_enabled","save_settings"]
        self.params.set_enabled(block_on_record,not record_in_progress)
        self.params.set_enabled(["batch_size"],self.v["limit_frames"] and not record_in_progress)
        self.params.set_enabled(["filesplit"],self.v["do_filesplit"] and not record_in_progress)
        self.params.set_enabled(["pretrigger_size","pretrigger_clear"],self.v["pretrigger_enabled"] and not record_in_progress)
        self.params.set_enabled(["log_event"],record_in_progress)
        self.params.set_enabled("snap_displayed",self.v["snap_display_source"]!=-1)
    @controller.exsafe
    def update_display_source_options(self, reset_value=False):
        frame_sources=self.cam_ctl.get_frame_sources()
        index_values,options=list(zip(*frame_sources.items()))
        self.params.w["snap_display_source"].set_options(options=options,index_values=index_values,value=index_values[0] if reset_value else None)
    def set_all_values(self, values):
        self.update_display_source_options()
        if "saving" in values:
            del values["saving"]
        if "default_snap_path" in values: # make sure it is changed first to not affect other settings
            self.v["default_snap_path"]=values["default_snap_path"]
        return super().set_all_values(values)





class SaveStatus_GUI(param_table.StatusTable):
    """
    Generic saving status table.

    Defines the saving status displays: number of frames received and saved, RAM status, pretrigger buffer status, etc.
    """
    def setup(self, ctl):
        super().setup("status_table",add_indicator=True)
        self.cam_ctl=ctl
        if self.cam_ctl.save_thread:
            self._finishing_saving_time=general.Countdown(0.5,start=False)
            self.add_status_line("saving",label="Saving:",srcs=self.cam_ctl.save_thread,tags="status/saving_text")
        self.add_num_label("frames/received",formatter=("int"),label="Frames received:")
        self.add_num_label("frames/scheduled",formatter=("int"),label="Frames scheduled:")
        self.add_num_label("frames/saved",formatter=("int"),label="Frames saved:")
        self.add_num_label("frames/missed",formatter=("int"),label="Frames missed:")
        self.add_text_label("frames/status_line_check",label="Status line:")
        self.add_text_label("frames/ram_status",label="Saving buffer:")
        self.add_num_label("frames/pretrigger_frames",formatter=("int"),label="Pretrigger frames:")
        self.add_num_label("frames/pretrigger_ram",formatter=("int"),label="Pretrigger RAM:")
        self.add_num_label("frames/pretrigger_skipped",formatter=("int"),label="Pretrigger missed:")
        self.add_padding()
    def show_parameters(self, params):
        """Update camera status lines"""
        for p in ["frames/received","frames/scheduled","frames/saved","frames/missed"]:
            if p in params:
                self.v[p]=params[p]
        missed_frames=params.get("frames/missed")
        if missed_frames is not None:
            self.w["frames/missed"].setStyleSheet("color: red; font-weight: bold" if missed_frames else "")
        if "frames/queue_ram" in params:
            self.v["frames/ram_status"]="{:.0f} / {:.0f} MB".format(params["frames/queue_ram"]/2**20,params["frames/max_queue_ram"]/2**20)
        if "frames/pretrigger_status" in params and params["frames/pretrigger_status"] is not None:
            stats=params["frames/pretrigger_status"]
            self.v["frames/pretrigger_frames"]="{} / {}".format(stats.frames,stats.size)
            self.v["frames/pretrigger_skipped"]="{}".format(stats.skipped)
            self.w["frames/pretrigger_skipped"].setStyleSheet("color: red; font-weight: bold" if stats.skipped else "")
            if stats.frames>0:
                est_tot_size=(stats.size/stats.frames)*stats.nbytes
                self.v["frames/pretrigger_ram"]="{:.0f} / {:.0f} MB".format(stats.nbytes/2**20,est_tot_size/2**20)
            else:
                self.v["frames/pretrigger_ram"]="0 / 0 MB"
        else:
            self.v["frames/pretrigger_frames"]="0 / 0"
            self.v["frames/pretrigger_skipped"]="0"
            self.w["frames/pretrigger_skipped"].setStyleSheet("")
            self.v["frames/pretrigger_ram"]="0 / 0 MB"
        if self.cam_ctl.save_thread:
            if self.v["saving"]=="Finishing saving":
                self._finishing_saving_time.trigger(restart=False)
            else:
                self._finishing_saving_time.stop()
            self.w["saving"].setStyleSheet("background: gold; color: black" if self._finishing_saving_time.passed() else "")
        if "frames/status_line_check" in params:
            slc=params["frames/status_line_check"]
            slc_ok=slc in {"off","na","none"}
            slc_good=slc=="ok"
            slc_statuses={"off":"Not enabled","ok":"OK","na":"No frames","none":"No status line found",
                "out_of_oder":"Frames out of order","still":"Duplicate frames","skip":"Skipping frames"}
            slc_text=slc_statuses.get(slc,"Unknown")
            self.v["frames/status_line_check"]=slc_text
            if slc_good:
                self.w["frames/status_line_check"].setStyleSheet("color: green")
            elif slc_ok:
                self.w["frames/status_line_check"].setStyleSheet("")
            else:
                self.w["frames/status_line_check"].setStyleSheet("color: red; font-weight: bold")