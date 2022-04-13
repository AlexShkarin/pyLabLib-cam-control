"""
Module contained base for filter classes.
"""

import numpy as np



class IFrameFilter:
    """
    Base class for custom filters; any filter should inherit from this class (or implement the same interface).

    Interaction of the filter with the GUI is governed by several functions:
    :meth:`get_desc` for getting filter description and list of parameters,
    :meth:`apply_settings` for getting parameter values from GUI,
    :meth:`get_settings` for sending parameter values to GUI for display,
    and :meth:`get_status` for getting immediate status parameters (difference from :meth:`get_settings` is in the description).

    Processing of the frames is governed by 2 functions:
    :meth:`receive_frames` for receiving data from the camera, and :meth:`generate_frame` for sending processed frames back to the GUI.
    """
    _class_name=None  # class name (needs to be defined to appear in the list)
    _class_caption=None  # default class caption (by default, same as ``_class_name``)
    _class_description=None  # longer class description
    def __init__(self):
        self.description={"receive_all_frames":False,"gui/parameters":[]}
        if self._class_caption is not None:
            self.description["caption"]=self._class_caption
        if self._class_description is not None:
            self.description["description"]=self._class_description
        self.p={}
        self._plotter_selector=None
    @classmethod
    def get_class_name(cls, kind="name"):
        """
        Get plugin class name.

        `kind` can be ``"name"`` (code-friendly identifiers to use in, e.g., settings file)
        or ``"caption"`` (formatted name to be used in GUI lists, etc.)
        """
        if kind=="name":
            return cls._class_name or cls.__name__
        elif kind=="caption":
            return cls._class_caption or cls.get_class_name(kind="name")

    ## Setup and utility functions ##
    def setup_general(self, receive_all_frames=False):
        """
        Setup general filter parameters.
        
        Args:
            receive_all_frames: if ``True``, :meth:`receive_frames` is called for all frames received from the camera;
                otherwise, it is only called with a small subset of frames (this is to relieve the load from the inter-process communication,
                in case the filter operates only on a single frame); default is ``False``
        """
        self.description["receive_all_frames"]=receive_all_frames
    def add_parameter(self, name, label=None, kind="float", limit=(None,None), fmt=None, options=None, default=None, indicator=False):
        """
        Add a GUI parameter.

        Args:
            name: parameter name; used to define the parameter in :meth:`get_settings` and :meth:`apply_settings`;
                should follow same convention as Python variable names (only letters, digits and underscore symbol)
            label: parameter label to be displayed in GUI; by default, same as `name`
            kind: parameter kind; can be ``"text"``, ``"float"``, ``"int"``, ``"button"``, ``"check"``, or ``"select"``
            limit: parameter limits ``(lower, upper)`` (only for numerical parameters); ``None`` means no limits; by default, no limits
            fmt: parameter representation format for numerical parameters; see :func:`pylablib.core.gui.format.as_formatter` for details
            options: for ``"select"`` kind, a dictionary ``{value: caption}`` for the combobox values
            default: default parameter value to set in the parameter ``p`` dictionary and in the GUI;
                by default, 0 for numerical controls, ``False`` for checkboxes, first element for combo boxes
            indicator: if ``True``, the variable is used only for indication on a separate panel;
                in this case, only ``"text"``, ``"float"``, or ``"int"`` kinds are allowed
        """
        if name in self.p:
            raise ValueError("parameter {} is already defined".format(name))
        allowed_kinds=["text","float","int","virtual"] if indicator else ["text","float","int","button","check","select","virtual"]
        if kind not in allowed_kinds:
            raise ValueError("unrecognized parameter kind: {}; allowed parameters are {}".format(kind,allowed_kinds))
        if label is None:
            label=name
        if default is None:
            if kind in ["float","int"]:
                default=limit[0] or 0
            elif kind=="check":
                default=False
            elif kind=="select":
                default=list(options)[0]
        self.description["gui/parameters"].append({"name":name,"label":label,"kind":kind,"limit":limit,"fmt":fmt,"options":options or {},"default":default,"indicator":indicator})
        self.p[name]=default
    def select_plotter(self, selector):
        """Select a specific plotter settings set"""
        self._plotter_selector=selector

    ## Setup functions ##
    def setup(self):
        """
        Filter setup.

        Called when the filter is loaded.
        All the setup functionality should ideally be added here rather than in the constructor.
        """
    def cleanup(self):
        """
        Clean up filter data.

        Called when the filter is stopped can closed (on the application shutdown, or when a different filter is loaded).
        """
    
    ## Parameter control functions ##
    def get_all_parameters(self):
        """
        Get all filter parameters to display in GUI indicators.

        Method is called periodically to update current settings display in filter settings table.
        Return dictionary ``{name: value}`` with settings parameters. Parameter names are defined in :meth:`add_parameter`.
        In principle, can return only subset of parameters, in which case other parameters will keep displaying previous values.
        By default, return a dictionary of all values returned by :meth:`get_parameter`.
        """
        return {p["name"]:self.get_parameter(p["name"]) for p in self.description["gui/parameters"]}
    def get_parameter(self, name):
        """
        Get filter parameter value to display in GUI indicators.

        Method is called periodically to update current settings display in filter settings table.
        By default, return the value in ``p`` attribute.
        """
        return self.p[name]
    def set_parameter(self, name, value):
        """
        Set a single filter parameter value.

        Method is used for controlling filter settings from GUI; it is called whenever a parameter value is changed in GUI.
        Parameter name is same as defined in :meth:`add_parameter`.

        By default, set value in ``p`` attribute.
        """
        self.p[name]=value
    
    ## Main computation functions ##
    def receive_frames(self, frames):
        """
        Receive frames generated by a camera.

        `frames` is a 3D numpy array, where the first axis is a frame number; the length of the first axis is always at least 1.
        """
    def generate_frame(self):
        """
        Generate a new frame to show.

        Method is called periodically (with the period defined by the image display update rate).
        Return a 2D numpy array; dtype and size can, in principle, differ from the original camera frames, although this is undesirable.
        Can also return ``None``, in which case the display is not updated (i.e., it means that there are no new frames to show).
        """
        return None
    def generate_data(self):
        """
        Generate new data to show.

        Method is called periodically (with the period defined by the image display update rate).
        Return a dictionary containing data to show. The keys are:
            ``"frame"``: frame to show in the frame plotter
                (2D array; by default, the one generated by :meth:`generate_frame`)
        """
        data={}
        frame=self.generate_frame()  # pylint: disable=assignment-from-none
        if frame is not None:
            data["frame"]=frame
        if self._plotter_selector is not None:
            data["plotter/selector"]=self._plotter_selector
        return data



class ISingleFrameFilter(IFrameFilter):
    """
    Frame filter designed to operate on single frames (i.e., it doesn't require frames 'history').

    Overloads standard :meth:`receive_frames` and :meth:`generate_frame` methods and defines a new method :meth:`process_frames`
    Normally, this filer would go with ``"receive_all_frames"`` parameter to be ``False`` in the description.

    Examples are frame gaussian blur (or any kind of convolution) or Fourier transform.
    """
    def setup(self):
        super().setup()
        self._latest_frame=None
    def receive_frames(self, frames):
        self._latest_frame=frames[-1].copy()
    def generate_frame(self):
        return self.process_frame(self._latest_frame) if (self._latest_frame is not None) else None
    def process_frame(self, frame):
        """
        Process a single frame and return the result.

        `frame` is a 2D numpy array containing a single camera frames.
        """
        return frame




class IMultiFrameFilter(IFrameFilter):
    """
    Frame filter designed to operate on last N frames (i.e., it depends 'history').

    Overloads standard :meth:`receive_frames` and :meth:`generate_frame` methods and defines a new method :meth:`process_buffer`.
    Also it defines attribute ``buffer_size``, which determines the number of last frame to keep in memory;
    it can be altered depending on, e.g., GUI parameter settings.

    Examples are median background subtraction or sliding window average.
    """
    def setup(self, buffer_size=1, buffer_step=1, process_incomplete=False, add_length_status=True):
        """
        Setup the buffered filter.

        Args:
            buffer_size: initial buffer size (number of frames); can be changed later using :meth:`reshape_buffer`
            buffer_step: initial frame buffer step (only every `buffer_step` frame is stored in the buffer);
                can be changed later using :meth:`reshape_buffer`
            process_incomplete: if ``True``, :meth:`process_buffer` is always called when requested;
                otherwise, call only when the buffer is full
            add_length_status: if ``True``, automatically add a status line showing the current buffer fill status
        """
        super().setup()
        self.setup_general(receive_all_frames=True)
        self.buffer=[]
        self.buffer_size=buffer_size
        self.buffer_step=buffer_step
        self._buffer_step_part=0
        self.process_incomplete=process_incomplete
        if add_length_status:
            self.add_parameter("buff_accum",label="Accumulated frames",kind="text",indicator=True)
    def reshape_buffer(self, buffer_size=None, buffer_step=None):
        """Change buffer size and the step between the frames"""
        if buffer_size is not None:
            self.buffer_size=max(buffer_size,1)
            self.buffer=self.buffer[-self.buffer_size:]
        if buffer_step is not None and buffer_step!=self.buffer_step:
            self.buffer_step=buffer_step
            self._buffer_step_part=0
            self.buffer=[]
    def receive_frames(self, frames):
        if self.buffer and self.buffer[0].shape!=frames.shape[1:]:
            self.buffer=[]
        start=self.buffer_step-self._buffer_step_part-1
        self._buffer_step_part=(len(frames)+self._buffer_step_part)%self.buffer_step
        frames=frames[start::self.buffer_step]
        self.buffer+=list(frames)
        if len(self.buffer)>self.buffer_size:
            del self.buffer[:len(self.buffer)-self.buffer_size]
        if "buff_accum" in self.p:
            self.p["buff_accum"]="{} / {}".format(len(self.buffer),self.buffer_size)
    def generate_frame(self):
        return self.process_buffer(self.buffer[:self.buffer_size]) if self.process_incomplete or len(self.buffer)>=self.buffer_size else None
    def process_buffer(self, buffer):
        """
        Process buffer containing last ``self.buffer_size`` frames.

        `buffer` is a list of 2D numpy arrays; it is guaranteed to have length of ``self.buffer_size`` (frames are not generated during the 'accumulation' phase),
        and that all frames have the same size (if the size is ever changed, the buffer is reset).
        """
        return buffer[-1]




class IRingMultiFrameFilter(IFrameFilter):
    """
    Similar to :class:`IMultiFrameFilter`, but instead of list uses a numpy array to implement a ring buffer.

    Somewhat harder to use than :class:`IMultiFrameFilter`, but has a bit better performance.
    """
    def setup(self, buffer_size=1, buffer_step=1, process_incomplete=False, add_length_status=True):
        """
        Setup the buffered filter.

        Args:
            buffer_size: initial buffer size (number of frames); can be changed later using :meth:`reshape_buffer`
            buffer_step: initial frame buffer step (only every `buffer_step` frame is stored in the buffer);
                can be changed later using :meth:`reshape_buffer`
            process_incomplete: if ``True``, :meth:`process_buffer` is always called when requested;
                otherwise, call only when the buffer is full
            add_length_status: if ``True``, automatically add a status line showing the current buffer fill status
        """
        super().setup()
        self.setup_general(receive_all_frames=True)
        self.buffer=None
        self.buffer_size=buffer_size
        self.buffer_step=buffer_step
        self.process_incomplete=process_incomplete
        self._buffer_step_part=0
        self.end_pos=0 # position after the last added frame
        self.filled=False # whether the buffer has been filled after reset
        if add_length_status:
            self.add_parameter("buff_accum",label="Accumulated frames",kind="text",indicator=True)
    def reshape_buffer(self, buffer_size=None, buffer_step=None, frame_shape=None, frame_dtype=None):
        """
        Change buffer shape, data type, and step between the frames..
        
        If any parameter is ``None``, it keeps its previous value.
        This method should always be used to change ``self.buffer_size``, otherwise the change has no effect
        """
        if buffer_size is not None:
            self.buffer_size=buffer_size
        if frame_shape is None and self.buffer is not None:
            frame_shape=self.buffer.shape[1:]
        if frame_dtype is None and self.buffer is not None:
            frame_dtype=self.buffer.dtype
        if frame_shape is not None and frame_dtype is not None:
            new_shape=(self.buffer_size,)+frame_shape
            new_dtype=np.dtype(frame_dtype)
            if self.buffer is None or self.buffer.shape!=new_shape or self.buffer.dtype!=new_dtype:
                self.buffer=np.zeros(shape=new_shape,dtype=new_dtype)
        if buffer_step is not None and buffer_step!=self.buffer_step:
            self.buffer_step=buffer_step
            self._buffer_step_part=0
        self.end_pos=0
        self.filled=False
    def receive_frames(self, frames):
        if self.buffer is None or self.buffer.shape[1:]!=frames.shape[1:]:
            self.reshape_buffer(frame_shape=frames.shape[1:],frame_dtype=frames.dtype)
        start=self.buffer_step-self._buffer_step_part-1
        self._buffer_step_part=(len(frames)+self._buffer_step_part)%self.buffer_step
        frames=frames[start::self.buffer_step]
        if len(frames)>=len(self.buffer):
            self.buffer[:]=frames[-len(self.buffer):]
            self.end_pos=0
            self.filled=True
        elif len(frames)+self.end_pos>=len(self.buffer):
            frames_left=len(self.buffer)-self.end_pos
            self.buffer[self.end_pos:]=frames[:frames_left]
            self.buffer[:len(frames)-frames_left]=frames[frames_left:]
            self.end_pos=len(frames)-frames_left
            self.filled=True
        else:
            self.buffer[self.end_pos:self.end_pos+len(frames)]=frames
            self.end_pos+=len(frames)
        if "buff_accum" in self.p:
            self.p["buff_accum"]="{} / {}".format(len(self.buffer) if self.filled else self.end_pos,len(self.buffer))
    def generate_frame(self):
        if self.process_incomplete and not self.filled:
            return self.process_buffer(self.buffer,0,self.end_pos)
        return self.process_buffer(self.buffer,self.end_pos,len(self.buffer)) if self.filled else None # end_pos is also start_pos if buffer is filled
    def process_buffer(self, buffer, start, filled):
        """
        Process buffer containing last ``self.buffer_size`` frames.

        `buffer` is a 3D numpy array containing ``self.buffer_size`` frames
        (some of them might not be valid, if ``process_incomplete=True`` was supplied to :meth:`setup`);
        `start` is the position of the first buffer frame (i.e., the index of the oldest frame in the buffer).
        `filled` is the number of valid frames in the buffer; if ``self.process_incomplete==False`` (default),
        then the method is called only for filled buffers, so ``filled==len(buffer)``.
        If the buffer is full, then chronologically frames go from ``start`` to ``len(buffer)``,
        and then continue from ``0`` to ``start``; otherwise, they go from ``0`` till ``filled``.
        """
        return buffer[(start+filled-1)%len(buffer)]  # take the most recent valid frame