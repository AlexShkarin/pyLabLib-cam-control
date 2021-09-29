from pylablib.misc.file_formats import cam
from pylablib.devices import PhotonFocus
from pylablib.devices.interface import camera as camera_utils

from pylablib.core.thread import controller
from pylablib.core.utils import dictionary, files as file_utils, funcargparse
from pylablib.core.fileio import savefile, loadfile, table_stream, location
from pylablib.core.dataproc import image
from pylablib.thread.stream import frameproc, table_accum, stream_manager

import time
import collections
import numpy as np
import imageio
import os




########## Frame processing ##########

class FrameProcessorThread(frameproc.BackgroundSubtractionThread):
    def setup_task(self, src, tag_in, tag_out=None):
        super().setup_task(src,tag_in,tag_out=tag_out)
        self.subscribe_commsync(self.on_control_signal,tags="processing/control",limit_queue=100)
        self.add_command("load_settings")
        
    def on_control_signal(self, src, tag, msg):
        """
        Receive frame processing control signal.
        
        These signals control and coordinate behavior of all frame processors.
        """
        comm,value=msg
        if comm=="display_update_period":
            self.set_output_period(max(value,0.01))
    def load_settings(self, settings):
        """
        Apply settings from the settings file.

        Settings entries:
            ``status_line_policy``: determines way to deal with status lines;
                can be ``"keep"`` (keep as is), ``"cut"`` (cut off the status line row), ``"zero"`` (set it to zero),
                ``"median"`` (set it to the image median), or ``"duplicate"`` (set it equal to the previous row; default)
        """
        self.status_line_policy=settings.get("status_line_policy","duplicate")
        if self.status_line_policy not in {"keep","cut","zero","median","duplicate"}:
            self.status_line_policy="duplicate"


FrameBinningThread=frameproc.FrameBinningThread
FrameSlowdownThread=frameproc.FrameSlowdownThread


##### Camera channel calculation #####

class ChannelAccumulator(controller.QTaskThread):
    """
    Channel accumulator.

    Receives frames from a source, calculate time series and accumulates in a table together with the frame indices.

    Setup args:
        - ``settings``: dictionary with the accumulator settings

    Commands:
        - ``enable``: enable or disable accumulation
        - ``add_source``: add a frame source
        - ``select_source``: select one of frame sources for calculation
        - ``setup_processing``: setup processing parameters
        - ``setup_roi``: setup averaging ROI
        - ``reset_roi``: reset averaging ROI to the whole image
        - ``get_data``: get the accumulated data as a dictionary of 1D numpy arrays
        - ``reset``: clear the accumulation table
    """
    def setup_task(self, settings=None):
        self.settings=settings or {}
        self.frame_channels=["idx","mean"]
        self.memsize=self.settings.get("memsize",100000)
        self.table_accum=table_accum.TableAccumulator(channels=self.frame_channels,memsize=self.memsize)
        self.enabled=False
        self.current_source=None
        self.sources={}
        self.cnt=stream_manager.StreamIDCounter()
        self.skip_count=1
        self._skip_accum=0
        self.reset_time=time.time()
        self.roi=None
        self.roi_enabled=False
        self._last_roi=None
        self.add_command("enable")
        self.add_command("add_source")
        self.add_command("select_source")
        self.add_command("setup_processing")
        self.add_command("setup_roi")
        self.add_command("reset_roi")
        self.add_command("get_data")
        self.add_command("reset")

    def enable(self, enabled=True):
        """Enable or disable trace accumulation"""
        self.enabled=enabled
        self._skip_accum=0
    def setup_processing(self, skip_count=1):
        """
        Setup processing parameters.

        Args:
            skip_count: the accumulated values are calculated for every `skip_count` frame.
        """
        self.skip_count=skip_count
        self._skip_accum=0

    TSource=collections.namedtuple("TSource",["src","tag","kind","sync"])
    def add_source(self, name, src, tag, sync=False, kind="raw"):
        """
        Add a frame source.

        Args:
            name: source name (used for switching source)
            src: frame signal source
            tag: frame signal tag
            sync: if ``True``, the subscription is synchronized to the source (i.e, if processing takes too much time, the frame source waits);
                otherwise, the subscription is not synchronized (if processing takes too much time, frames are skipped)
            kind: source kind; can be ``"raw"`` (plotted vs. frame index, reset on source restart), ``"show"`` (plotted vs. time, only reset explicitly),
                or ``"points"`` (source sends directly a dictionary of trace values rather than frames)
        """
        self.sources[name]=self.TSource(src,tag,kind,sync)
        callback=lambda s,t,v: self.process_source(s,t,v,source=name)
        if sync:
            self.subscribe_commsync(callback,srcs=src,tags=tag,dsts="any",limit_queue=2,on_full_queue="wait")
        else:
            self.subscribe_commsync(callback,srcs=src,tags=tag,dsts="any",limit_queue=10)
    def select_source(self, name):
        """Select a source with a given name"""
        if self.current_source!=name:
            self.reset()
            self.cnt=stream_manager.StreamIDCounter()
            self.current_source=name
            if self.sources[name].kind in {"raw","show"}:
                self.table_accum.change_channels(self.frame_channels)
            else:
                self.table_accum.change_channels([])
    
    def setup_roi(self, center=None, size=None, enabled=True):
        """
        Setup averaging ROI parameters.

        `center` and `size` specify ROI parameters (if ``None``, keep current values).
        `enabled` specifies whether ROI is applied for averaging (``enabled==True``), or the whole frame is averaged (``enabled==False``)
        Return the new ROI (or ``None`` if no ROI can be specified).
        """
        if center is not None or size is not None:
            if center is None and self.roi is not None:
                center=self.roi.center()
            if size is None and self.roi is not None:
                size=self.roi.size()
            if center is not None and size is not None:
                self.roi=image.ROI.from_centersize(center,size)
        self.roi_enabled=enabled
        return self.roi
    def reset_roi(self):
        """
        Reset ROI to the whole image

        Return the new ROI (or ``None`` if no frames have been acquired, so no ROI can specified)
        """
        self.roi=self._last_roi
        return self.roi
    def process_frame(self, value, kind):
        """Process raw frames data"""
        if not value:
            return
        if self.cnt.receive_message(value):
            self.reset()
        skip_count=self.skip_count if kind=="raw" else 1
        frames,indices,_=value.get_slice((-self._skip_accum)%skip_count,step=skip_count)
        self._skip_accum=(self._skip_accum+value.nframes())%skip_count
        status_line=value.metainfo.get("status_line")
        for i,f in zip(indices,frames):
            if f.ndim==2:
                f=f[None,...]
                i=[i]
            calc_roi=self.roi if (self.roi and self.roi_enabled) else image.ROI(0,f.shape[-2],0,f.shape[-1])
            sums,area=image.get_region_sum(f,calc_roi.center(),calc_roi.size())
            if status_line is not None:
                sl_roi=camera_utils.get_status_line_roi(f,status_line)
                sl_roi=image.ROI.intersect(sl_roi,calc_roi)
                if sl_roi:
                    sl_sums,sl_area=image.get_region_sum(f,sl_roi.center(),sl_roi.size())
                    sums-=sl_sums
                    area-=sl_area
            means=sums/area if area>0 else sums
            if kind=="raw":
                x_axis=i
            else:
                x_axis=[time.time()-self.reset_time]*len(means)
            self.table_accum.add_data([x_axis,means])
        shape=value.first_frame().shape
        self._last_roi=image.ROI(0,shape[0],0,shape[1])
    def process_points(self, value):
        """Process trace dictionary data"""
        table={}
        min_len=None
        for k in value:
            v=value[k]
            if not isinstance(v,(list,np.ndarray)):
                v=[v]
            table[k]=v
            min_len=len(v) if min_len is None else min(len(v),min_len)
        if min_len>0:
            for k in table:
                table[k]=table[k][:min_len]
            if "idx" not in table:
                table["idx"]=[time.time()-self.reset_time]*min_len
            if not self.table_accum.channels:
                self.table_accum.change_channels(list(table.keys()))
            self.table_accum.add_data(table)
    def process_source(self, src, tag, value, source):
        """Receive the source data (frames or traces), process and add to the accumulator table"""
        if not self.enabled or source!=self.current_source:
            return
        kind=self.sources[source].kind
        if kind in {"raw","show"}:
            self.process_frame(value,kind)
        elif kind=="points":
            self.process_points(value)
    def get_data(self, maxlen=None):
        """
        Get the accumulated data as a dictionary of 1D numpy arrays.
        
        If `maxlen` is specified, get at most `maxlen` datapoints from the end.
        """
        return self.table_accum.get_data_dict(maxlen=maxlen)
    def reset(self):
        """Clear all data in the table"""
        self.table_accum.reset_data()
        self._skip_accum=0
        self.reset_time=time.time()




########## Frame saving ##########

class PretriggerBuffer:
    """
    Pretrigger buffer.

    Keeps track of the added frames and the total size, finds skips frames.

    Args:
        size: maximal buffer size
        strict_size: if ``True``, the number of the frames in the buffer is never greater than `size`;
            otherwise, the frame number is quantized to the whole frame messages, so the size might be larger.
        clear_on_reset: if ``True`` and a message with the reset signature (zero start index) is added, clear the buffer before adding.
    """
    def __init__(self, size, strict_size=True, clear_on_reset=True):
        self.size=size
        self.buffer=[]
        self.current_size=0
        self.strict_size=strict_size
        self.clear_on_reset=clear_on_reset
    
    def add_frame_message(self, msg):
        """Add a new frame message"""
        if not msg:
            return
        if not msg.first_frame_index() and self.clear_on_reset:
            self.clear()
        self.buffer.append(msg)
        self.current_size+=msg.nframes()
        while self.buffer and self.current_size-self.buffer[0].nframes()>=self.size:
            self.current_size-=self.buffer[0].nframes()
            del self.buffer[0]
        if self.strict_size and self.current_size>self.size:
            extra_frames=self.current_size-self.size
            self.buffer[0].cut_to_size(self.buffer[0].nframes()-extra_frames,from_end=True)
            self.current_size-=extra_frames
    def pop_frame_message(self):
        """Pop the latest frame message"""
        if self.buffer:
            self.current_size-=self.buffer[0].nframes()
            return self.buffer.pop(0)
    def clear(self):
        """Clear all frames in the buffer"""
        self.buffer=[]
        self.current_size=0
    def copy(self):
        """Return copy of the buffer"""
        buff=PretriggerBuffer(self.size,self.strict_size,self.clear_on_reset)
        buff.buffer=list(self.buffer)
        buff.current_size=self.current_size
        return buff

    def has_frames(self):
        """Check if there are frames in the buffer"""
        return bool(self.buffer)
    def nframes(self):
        """Get total number of frames"""
        return sum([m.nframes() for m in self.buffer])
    def nbytes(self):
        """Get total size of the frames in bytes"""
        return sum([m.nbytes() for m in self.buffer])
    TBufferStatus=collections.namedtuple("TBufferStatus",["frames","skipped","nbytes","size"])
    def get_status(self):
        """
        Get buffer status.

        Return tuple ``(frames, skipped, nbytes, size)`` with, corresobondingly, number of frames in the buffer, number of skipped frames amongst them,
        size of the buffer in bytes, and maximal buffer size.
        """ 
        last_frame_idx=None
        nframes=self.nframes()
        nbytes=self.nbytes()
        skipped=0
        for m in self.buffer:
            skipped+=m.get_missing_frames_number(last_frame_idx if m.first_frame_index() else None) # don't count reset as skip
            last_frame_idx=m.last_frame_index()
        return self.TBufferStatus(nframes,skipped,nbytes,self.size)

class FrameWriteError(IOError):
    """Frame saving error"""
    def __init__(self, saved=0):
        self.saved=saved
        super().__init__("error saving frames: only {} frames saved".format(saved))

class FrameSaveThread(controller.QTaskThread):
    """
    Frame saving thread

    Receives frame signals, and saves the frames to the disk.

    Setup args:
        src: frames source
        tag: frames signal tag
        settings_mgr: settings manager thread name (used to save settings file on saving start)
        frame_processor: frame processor thread name (used to get snapshot background to save to the file, if appropriate)

    Attributes:
        chunks_per_save: number of saving queue chunks to write to disk in one dump job (by default, one chunk)
        chunk_period (float): duration of a single saving queue chunk (in seconds); by default, 0.5 seconds
        dumping_period (float): period of queue dump job; by default, 0.1 seconds

    Variables:
        path: saving path
        batch_size: saving batch size (limit on the total number of frames saved)
        received: total frames received since the saving started
        scheduled: total frames scheduled for saving since the saving started (received frame is scheduled unless queue RAM is overflowing)
        saved: total frames saved since the saving started
        missed: total number of frames missed in saving since the saving stated (based on frames indices)
        pretrigger_status: tuple with the pretrigger status (see :meth:`PretriggerBuffer.get_status`), or ``None`` if pretrigger is disabled
        queue_ram: current occupied queue RAM size
        max_queue_ram: maximal queue RAM size
        status_line_check: status line check status; can be ``"off"`` (check is off), ``"none"`` (frames don't have status line), ``"na"`` (no frames have been received yet),
            ``"ok"`` (status line check is ok), ``"missing"`` (missing frames), ``"still"`` (repeating frames), or ``"out_of_order"`` (later frames have lower index).

    Commands:
        save_start: start streaming
        save_stop: stop streaming
        setup_pretrigger: setup pretrigger buffer
        clear_pretrigger: clear pretrigger buffer
        setup_queue_ram: setup maximal saving queue RAM
    """
    def setup_task(self, src, tag, settings_mgr=None, frame_processor=None):
        self.subscribe_commsync(self.receive_frames,srcs=src,tags=tag,limit_queue=100)
        self.settings_mgr=settings_mgr
        self._cam_settings_time="before" # ``"before"`` - get full camera settings in the beginning of saving; ``"after"`` - get them in the end of saving
        self.frame_processor=frame_processor
        self._save_queue=None
        self._pretrigger_buffer=None
        self._clear_pretrigger_on_write=True
        self._saving=False
        self._stopping=False
        self.sync_period=0.1
        self.v["path"]=None
        self.v["path_kind"]="pfx"
        self.v["batch_size"]=None
        self.v["saved"]=0
        self.v["received"]=0
        self.v["scheduled"]=0
        self.v["missed"]=0
        self.v["pretrigger_status"]=None
        self.append=False
        self.filesplit=None
        self.format="raw"
        self.background_desc={}
        self._file_idx=0
        self.chunks_per_save=1
        self.chunk_period=0.2
        self.dumping_period=0.02
        self._event_log_started=False
        self._start_time=None
        self._first_frame_recvd=None
        self._first_frame_idx=None
        self._first_frame_sid=None
        self._last_frame_recvd=None
        self._last_frame_idx=None
        self._last_frame_sid=None
        self._last_frame=None
        self._last_chunk_start=0
        self._tiff_writer=None
        self.v["max_queue_ram"]=2**30*4
        self._update_queue_ram(0)
        self.v["status_line_check"]="off"
        self._last_frame_statusline_idx=None
        self._perform_status_check=False
        self.update_status("saving","stopped",text="Saving done")
        self.add_command("save_start",self.save_start)
        self.add_command("save_stop",self.save_stop)
        self.add_command("setup_queue_ram",self.setup_queue_ram)
        self.add_command("write_event_log",self.write_event_log)
        self.add_command("setup_pretrigger",self.setup_pretrigger)
        self.add_command("clear_pretrigger",self.clear_pretrigger)
        self.add_job("dump_queue",self.dump_queue,self.dumping_period)
        
    
    def setup_pretrigger(self, size, enabled=True, preserve_frames=True, clear_on_write=True):
        """
        Setup pretrigger.

        Args:
            size (int): maximal pretrigger size
            enabled (bool): whether pretrigger is enabled
            preserve_frames (bool): if ``True``, preserve frames already in the buffer when changing its size; otherwise, clear the buffer.
            clear_on_write (bool): if ``True``, the buffer freames are removed from it when they are saved (default behavior); otherwise, the buffer state is preserved
                keep in mind that it's not updated during save (so there will be a gap for newly-added frames);
                generally, only makes sense to set ``clear_on_write=False`` for single-frame buffers
        """
        if enabled:
            if not (self._pretrigger_buffer and self._pretrigger_buffer.size==size):
                curr_buffer=self._pretrigger_buffer
                self._pretrigger_buffer=PretriggerBuffer(size)
                if curr_buffer and preserve_frames:
                    while curr_buffer.has_frames():
                        self._pretrigger_buffer.add_frame_message(curr_buffer.pop_frame_message())
        else:
            self._pretrigger_buffer=None
        self._clear_pretrigger_on_write=clear_on_write
        self.v["pretrigger_status"]=self._pretrigger_buffer.get_status() if self._pretrigger_buffer else None
    def clear_pretrigger(self):
        """Clear the pretrigger buffer"""
        if self._pretrigger_buffer:
            self._pretrigger_buffer.clear()
            self.v["pretrigger_status"]=self._pretrigger_buffer.get_status()
    def setup_queue_ram(self, max_queue_ram):
        self.v["max_queue_ram"]=max_queue_ram
        # self._frame_scheduler.change_max_size((self._frame_scheduler.max_size[0],self.v["max_queue_ram"]))
    def _update_queue_ram(self, queue_ram=None):
        if queue_ram is not None:
            self.v["queue_ram"]=queue_ram
        # self._frame_scheduler.change_max_size((self._frame_scheduler.max_size[0],self.v["max_queue_ram"]-self.v["queue_ram"]))
    def dump_queue(self):
        """Dump one or several chunks from the saving queue to the disk"""
        queue_empty=False
        append=(self.v["saved"]>0) or self.append
        for _ in range(self.chunks_per_save):
            new_chunk=self._save_queue.pop(0) if self._save_queue else []
            queue_empty=not self._save_queue
            if new_chunk:
                if self._first_frame_idx is None:
                    self._first_frame_idx=new_chunk[0].first_frame_index()
                    self._first_frame_sid=new_chunk[0].sid
                chunk_size=sum([msg.nbytes() for msg in new_chunk])
                self._update_queue_ram(self.v["queue_ram"]-chunk_size)
                flat_chunk=[f for m in new_chunk for f in m.frames]
                if self._perform_status_check:
                    if self.v["status_line_check"] in {"ok","na"}:
                        self.v["status_line_check"]=self._check_status_line(flat_chunk,step=new_chunk[0].metainfo["step"])
                try:
                    self._write_frames(flat_chunk,append=append)
                    self._write_frame_info(new_chunk,self._get_frame_info_path(),append=append)
                except FrameWriteError as err:
                    self.v["nsaved"]=err.saved
                    self.save_stop()
                    self._save_queue.clear()
                    self.queue_empty=True
                self.v["saved"]+=sum([msg.nframes() for msg in new_chunk])
                append=True
            if queue_empty:
                if self._stopping:
                    self._finalize_saving()
                    self._saving=False
                    self._stopping=False
                    self.update_status("saving","stopped",text="Saving done")
                else:
                    self.sleep(0.02)
                break
    def _finalize_saving(self):
        self._write_finish()
        if self._event_log_started:
            self.write_event_log("Recording stopped")
        self.finalize_settings()

    @staticmethod
    def build_path(base, path_kind="pfx", default_name="frames", subpath=None, idx=None, ext=None):
        """
        Make a data path from the base path depending on its kind.

        Args:
            base: base storage path
            path_kind: base path kind; either ``"pfx"``(add subpath as suffix to the base name),
                or ``"folder"`` (treat it as a folder, generate subpaths inside it)
            default_name: default file name if ``path_kind=="folder"``
            subpath: added as suffix if ``path_kind=="pfx"`` or defines a storage path if ``path_kind=="folder"``
            idx: if defined, adds an index suffix to the file name
            ext: path extension
        """
        funcargparse.check_parameter_range(path_kind,"path_kind",["pfx","folder"])
        bname,bext=os.path.splitext(base)
        idx_sfx="" if idx is None else "_{:04d}".format(idx)
        if path_kind=="pfx":
            loc=location.PrefixedFileSystemDataLocation(bname+idx_sfx+bext)
        else:
            loc=location.FolderFileSystemDataLocation(bname,default_name=default_name+idx_sfx,default_ext=bext[1:])
        return loc.get_filesystem_path((subpath,ext))
    def _make_path(self, subpath=None, idx=None, ext=None):
        return self.build_path(self.v["path"],path_kind=self.v["path_kind"],subpath=subpath,idx=idx,ext=ext)
    def _clean_path(self, subpath=None, idx=None, ext=None):
        """Clean saving path (remove file with this path if it exists)"""
        path=self._make_path(subpath=subpath,idx=idx,ext=ext)
        if os.path.exists(path):
            file_utils.retry_remove(path)
    def _get_settings_path(self):
        """Generate save path for settings file"""
        return self._make_path(subpath="settings",ext="dat")
    def _get_frame_info_path(self):
        """Generate save path for frame info table file"""
        return self._make_path(subpath="frameinfo",ext="dat")
    def _get_settings(self):
        """Get settings dictionary for the saver thread"""
        return {"path":file_utils.normalize_path(self.v["path"]),
                "path_kind":self.v["path_kind"],
                "batch_size":self.v["batch_size"],
                "chunk_size":self.filesplit or self.v["batch_size"],
                "append":self.append,
                "format":self.format,
                "background":self.background_desc,
                "start_timestamp":time.time(),
                "pretrigger_status/start":self.v["pretrigger_status"]}
    def _get_finalized_settings(self):
        """Get finalized settings (additional info at the end of saving process)"""
        settings={}
        for s in ["saved","scheduled","missed","received","status_line_check"]:
            settings[s]=self.v[s]
        settings["first_frame_timestamp"]=self._first_frame_recvd
        settings["first_frame_index"]=self._first_frame_idx
        settings["first_frame_session"]=self._first_frame_sid
        settings["last_frame_timestamp"]=self._last_frame_recvd
        settings["last_frame_index"]=self._last_frame_idx
        settings["last_frame_session"]=self._last_frame_sid
        settings["stop_timestamp"]=time.time()
        settings["pretrigger_status/stop"]=self.v["pretrigger_status"]
        if self._last_frame is not None:
            settings["frame/shape"]=self._last_frame.shape
            settings["frame/dtype"]=self._last_frame.dtype.str
        return settings
    def _get_manager_settings(self, include=None, exclude=None, alias=None):
        if self.settings_mgr:
            try:
                settings_mgr=controller.get_controller(self.settings_mgr,sync=False)
                return settings_mgr.cs.get_all_settings(include=include,exclude=exclude,alias=alias)
            except controller.threadprop.NoControllerThreadError:
                pass
        return {}
    def write_settings(self, extra_settings=None):
        """Collect full settings dictionary and save it to the disk"""
        if self._cam_settings_time=="before":
            settings=self._get_manager_settings(exclude=["cam/settings"]) or dictionary.Dictionary()
        else:
            settings=self._get_manager_settings(exclude=["cam"],alias={"cam/settings":"cam/settings_start"}) or dictionary.Dictionary()
        settings["save"]=self._get_settings()
        if extra_settings is not None:
            settings["extra"]=extra_settings
        savefile.save_dict(settings,self._get_settings_path())
    def finalize_settings(self):
        """Save finalized settings to the file"""
        path=self._get_settings_path()
        if os.path.exists(path):
            settings=loadfile.load_dict(path)
            settings.update(self._get_finalized_settings(),"save")
            if self._cam_settings_time!="before":
                settings.merge(self._get_manager_settings(include=["cam"]).get("cam",{}),path="cam")
            settings.merge(self._get_manager_settings(include=["cam/cnt"]).get("cam/cnt",{}),path="cam/cnt_after")
            savefile.save_dict(settings,path)

    def _get_background_path(self):
        """Generate save path for background file"""
        return self._make_path(subpath="background",ext="bin")
    def _get_snapshot_background_parameters(self):
        if self.frame_processor:
            try:
                frame_processor=controller.get_controller(self.frame_processor,sync=False)
                return frame_processor.get_background_to_save(),frame_processor.v["snapshot/parameters"]
            except controller.threadprop.NoControllerThreadError:
                pass
        return None,None
    def write_background(self):
        """Get background from the frame processor and save it to the disk"""
        background,params=self._get_snapshot_background_parameters()
        if background is not None:
            background=np.array(background)
            save_dtype="<f8" if background.dtype.kind=="f" else "<u2"
            with open(self._get_background_path(),"wb") as f:
                np.asarray(background,save_dtype).tofile(f)
            bg_saving_mode="only_bg" if len(background)==1 else "all"
            self.background_desc={"size":len(background),"dtype":save_dtype,"shape":background.shape[1:],"format":"bin","bg_params":params,"saving_mode":bg_saving_mode}
        else:
            self.background_desc={"saving_mode":"none"}

    
    def _get_event_log_path(self):
        """Generate save path for event log file"""
        return self._make_path(subpath="eventlog",ext="dat")
    def write_event_log(self, msg):
        """Write a text message into the event log"""
        if self._saving:
            path=self._get_event_log_path()
            preamble=""
            if not self._event_log_started:
                if os.path.exists(path):
                    if self.append:
                        preamble="\n\n"
                    else:
                        file_utils.retry_remove(path)
                        preamble="# Timestamp\tElapsed\tFrame\tMessage\n"
                preamble+="{:.3f}\t{:.3f}\t{:d}\t{}\n".format(self._start_time,0,self._first_frame_idx or 0,"Recording started")
            with open(path,"a") as f:
                t=time.time()
                line="{:.3f}\t{:.3f}\t{:d}\t{}\n".format(t,t-self._start_time,self._last_frame_idx or 0,msg)
                if preamble:
                    f.write(preamble)
                f.write(line)
            self._event_log_started=True

    def _check_status_line(self, frames, step=1):
        for f in frames:
            lines=PhotonFocus.get_status_lines(f,check_transposed=False)
            if lines.ndim==1:
                lines=lines[None,:]
            if lines is None or lines.shape[1]<2:
                return "none"
            indices=lines[:,0]
            if self._last_frame_statusline_idx is not None:
                indices=np.insert(indices,0,self._last_frame_statusline_idx)
            dfs=(indices[1:]-indices[:-1])%(2**24) # the internal counter is only 24-bit
            if np.any(dfs>2**23) or np.any((dfs>0)&(dfs<step)): # negative
                return "out_of_oder"
            if np.any(dfs==0):
                return "still"
            if np.any(dfs<step): # step smaller than should be
                return "out_of_oder"
            if np.any(dfs>step):
                return "skip"
            self._last_frame_statusline_idx=indices[-1]
        return "ok"

    def _write_tiff(self, frames):
        try:
            self._tiff_writer._meta["contiguous"]=False # force to flush after write to check the file size
        except AttributeError:
            pass
        if frames.ndim==3 and len(frames) in [3,4]: # can be confused with color-channel data
            self._tiff_writer.append_data(frames[:2])
            self._tiff_writer.append_data(frames[2:])
        else:
            self._tiff_writer.append_data(frames)
    def _write_frames(self, frames, append=True):
        """Write frames to the given path"""
        if self.format in ["cam"]:
            frames=[f for fs in frames for f in fs]
        nsaved=self.v["saved"]
        if frames:
            self._last_frame=frames[-1][-1,:].copy()
        if self.format=="cam":
            if self.filesplit is None:
                cam.save_cam(frames,self._make_path(),append=append)
            else: # file splitting mechanics
                while frames:
                    lchunk=(-nsaved-1)%self.filesplit+1
                    chunk,frames=frames[:lchunk],frames[lchunk:]
                    cam.save_cam(chunk,self._make_path(idx=self._file_idx),append=append)
                    nsaved+=len(chunk)
                    if nsaved%self.filesplit==0:
                        self._file_idx+=1
                        self._clean_path(idx=self._file_idx)
        elif self.format=="raw":
            save_dtype="<f8" if frames[0].dtype.kind=="f" else "<u2"
            mode="ab" if append else "wb"
            if self.filesplit is None:
                with open(self._make_path(),mode) as f:
                    for frm in frames:
                        np.asarray(frm,save_dtype).tofile(f)
            else: # file splitting mechanics
                f=None
                try:
                    for frm in frames:
                        frm_size=len(frm)
                        frm_saved=0
                        while frm_saved<frm_size:
                            lchunk=(-nsaved-1)%self.filesplit+1
                            frm_to_save=min(lchunk,frm_size-frm_saved)
                            if f is None:
                                f=open(self._make_path(idx=self._file_idx),mode)
                            np.asarray(frm[frm_saved:frm_saved+frm_to_save],save_dtype).tofile(f)
                            frm_saved+=frm_to_save
                            nsaved+=frm_to_save
                            if nsaved%self.filesplit==0:
                                f.close()
                                self._file_idx+=1
                                self._clean_path(idx=self._file_idx)
                                f=None
                finally:
                    if f is not None:
                        f.close()
        elif self.format in ["tiff","bigtiff"]:
            frames=[f.astype("float32") if f.dtype=="float64" else f for f in frames]
            if self.filesplit is None:
                if self._tiff_writer is None:
                    self._tiff_writer=imageio.get_writer(self._make_path(),format="tiff",bigtiff=self.format=="bigtiff",mode="V")
                for f in frames:
                    try:
                        self._write_tiff(f)
                        nsaved+=len(f)
                    except ValueError:
                        raise FrameWriteError(nsaved)
            else: # file splitting mechanics
                for frm in frames:
                    frm_size=len(frm)
                    frm_saved=0
                    while frm_saved<frm_size:
                        lchunk=(-nsaved-1)%self.filesplit+1
                        frm_to_save=min(lchunk,frm_size-frm_saved)
                        if self._tiff_writer is None:
                            self._tiff_writer=imageio.get_writer(self._make_path(idx=self._file_idx),format="tiff",bigtiff=self.format=="bigtiff",mode="V")
                        try:
                            self._write_tiff(frm[frm_saved:frm_saved+frm_to_save])
                            frm_saved+=frm_to_save
                            nsaved+=frm_to_save
                        except ValueError:
                            raise FrameWriteError(nsaved)
                        if nsaved%self.filesplit==0:
                            self._tiff_writer.close()
                            self._file_idx+=1
                            self._clean_path(idx=self._file_idx)
                            self._tiff_writer=None
    def _write_finish(self):
        """Finalize writing (applies only for tiff files)"""
        if self._tiff_writer:
            try:
                self._tiff_writer.close()
            except ValueError:
                pass
            self._tiff_writer=None

    def _write_frame_info(self, messages, path, append=True):
        """Write frame info in a table to the given path"""
        if not append and os.path.exists(path):
            file_utils.retry_remove(path)
        if all(msg.frame_info is None for msg in messages):
            return
        nsaved=self.v["saved"]
        header=None
        for msg in messages:
            header=msg.metainfo.get("frame_info_fields")
            if header is not None:
                header=["save_index"]+header
                break
        streamer=table_stream.TableStreamFile(path,columns=header,header_prepend="")
        for msg in messages:
            if msg.frame_info is not None:
                rows=[]
                for f,r in zip(msg.frames,msg.frame_info):
                    if r is not None:
                        if isinstance(r,np.ndarray) and r.ndim==2:
                            idx_col=np.arange(len(r))+nsaved
                            r=np.concatenate([idx_col[:,None],r],axis=1)
                            r=r[r[:,0]>=0]
                            rows+=list(r)
                        else:
                            rows.append([nsaved]+list(r))
                    nsaved+=(1 if f.ndim==2 else len(f))
                if rows:
                    streamer.write_multiple_rows(rows)



    def save_start(self, path, path_kind="pfx", batch_size=None, append=True, format="cam", filesplit=None, save_settings=False, perform_status_check=False, extra_settings=None):
        """
        Start saving routine.

        Args:
            path (str): the main saving path (can be modified for different saved files)
            path_kind (str): the kind of saving path; can be ``"pfx"`` (treat it as the main file path, aux files are generated by adding suffixes),
                or ``"folder"`` (treat it as folder, main and aux files are stored inside)
            batch_size: maximal number of frames to save (by default, no limit)
            append (bool): if ``True`` and the destination file already exists, append data to it; otherwise, remove it before saving
            format (str): file format; can be ``"cam"`` (.cam file), ``"raw"`` (raw binary in ``"<u2"`` format), or ``"tiff"`` (tiff format)
            filesplit: maximal number of frames per file (by default, all frames are in one file); if defined, file names acquire numerical suffix
            save_settings (bool): if ``True``, save all application setting to the file
            perform_status_check (bool): if ``True`` and frames have status line (applies only to Photon Focus cameras), check status line to ensure no missing frames
            extra_settings: can be a dictionary with additional settings to save to the settings file (saved in branch ``"extra"``)
        """
        if self._saving:
            self._finalize_saving()
            self.update_status("saving","stopped",text="Saving done")
        self.v["path"]=path
        funcargparse.check_parameter_range(path_kind,"path_kind",["pfx","folder"])
        self.v["path_kind"]=path_kind
        self.v["batch_size"]=batch_size
        self.append=append or (filesplit is not None)
        if format not in ["cam","raw","tiff","bigtiff"]:
            raise ValueError("unrecognized format: {}".format(format))
        self.format=format
        self.filesplit=filesplit
        self.v["saved"]=0
        self.v["scheduled"]=0
        self.v["received"]=0
        self.v["missed"]=0
        self._save_queue=[]
        self._event_log_started=False
        self._start_time=time.time()
        self._first_frame_recvd=None
        self._first_frame_idx=None
        self._first_frame_sid=None
        self._last_frame_recvd=None
        self._last_frame_idx=None
        self._last_frame_sid=None
        self._last_chunk_start=0
        self._update_queue_ram(0)
        self._stopping=False
        self._saving=True
        self._file_idx=0
        self.v["status_line_check"]="na" if perform_status_check else "off"
        self._last_frame_statusline_idx=None
        self._perform_status_check=perform_status_check
        file_utils.ensure_dir(os.path.split(self._make_path())[0])
        if filesplit is not None:
            self._clean_path()
        self.write_background()
        if save_settings:
            self.write_settings(extra_settings=extra_settings)
        self.update_status("saving","in_progress",text="Saving in progress")
        if self._pretrigger_buffer is not None:
            if not self._clear_pretrigger_on_write:
                old_buffer=self._pretrigger_buffer.copy()
            while self._pretrigger_buffer.has_frames():
                msg=self._pretrigger_buffer.pop_frame_message()
                scheduled=self.schedule_message(msg)
                if not scheduled:
                    break
            if not self._clear_pretrigger_on_write:
                self._pretrigger_buffer=old_buffer
        self.v["pretrigger_status"]=self._pretrigger_buffer.get_status() if self._pretrigger_buffer else None
    def save_stop(self):
        """Stop saving routine"""
        if self._saving and not self._stopping:
            self._stopping=True
            self.update_status("saving","stopping",text="Finishing saving")


    def _append_queue(self, msg):
        """Append frames to the saving queue"""
        last_chunk=[]
        if msg.metainfo["creation_time"]-self._last_chunk_start>self.chunk_period:
            self._last_chunk_start=msg.metainfo["creation_time"]
        elif self._save_queue:
            last_chunk=self._save_queue.pop()
        last_chunk.append(msg)
        self._save_queue.append(last_chunk)
    def schedule_message(self, msg):
        """
        Add frame message to the saving queue.

        Return ``True`` if the message was scheduled and ``False`` otherwise (number of frames reached the desired file size).
        """
        scheduled=False
        if self._saving and not self._stopping:
            if self.v["batch_size"] is not None:
                max_frames=self.v["batch_size"]-self.v["scheduled"]
                msg.cut_to_size(max_frames)
            tot_frames=msg.nframes()
            if tot_frames:
                if self._first_frame_recvd is None:
                    self._first_frame_recvd=msg.metainfo["creation_time"]
                self._last_frame_recvd=msg.metainfo["creation_time"]
                if self.v["queue_ram"]<=self.v["max_queue_ram"]:
                    self._append_queue(msg)
                    self._update_queue_ram(self.v["queue_ram"]+msg.nbytes())
                    self.v["missed"]+=msg.get_missing_frames_number(self._last_frame_idx if msg.first_frame_index() else None) # don't count reset as skip
                    self.v["scheduled"]+=tot_frames
                else:
                    self.v["missed"]+=msg.last_frame_index()-self._last_frame_idx if (self._last_frame_idx is not None) else msg.nframes()
                self._last_frame_idx=msg.last_frame_index()
                self._last_frame_sid=msg.sid
                self.v["received"]+=tot_frames
                scheduled=True
            if self.v["batch_size"] and self.v["scheduled"]>=self.v["batch_size"]:
                self.save_stop()
        return scheduled
    def receive_frames(self, src, tag, msg):
        """Process frame receive signal"""
        msg=msg.copy()
        scheduled=self.schedule_message(msg)
        if not scheduled and self._pretrigger_buffer is not None:
            self._pretrigger_buffer.add_frame_message(msg)
            self.v["pretrigger_status"]=self._pretrigger_buffer.get_status() if self._pretrigger_buffer else None