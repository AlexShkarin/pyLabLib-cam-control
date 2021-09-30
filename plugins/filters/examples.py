"""
Example module containing custom-defined filters.

To add a new filter, you need to define a filter class which subclasses from :class:`base.IFrameFilter` or one of its subclasses
(e.g., :class:`base.ISingleFrameFilter` or :class:`base.IMultiFrameFilter`) and define its ``_class_name`` attribute.
This class can be contained in any ``.py`` file withing this folder (``plugins/filters``).

See :class:`base.IFrameFilter` and filter examples in ``base.py`` and ``builtin.py`` for further info.
"""


from . import base

import numpy as np




class FrameRescaleFilter(base.ISingleFrameFilter):
    """
    Filter that rescales frame values (multiples them by ``self.p["mult"]`` and adds ``self.p["shift"]``)
    """
    # _class_name="rescale"  # class is only for illustration purposes
    _class_caption="Rescale"
    def setup(self):
        super().setup()
        self.add_parameter("shift",label="Shift")
        self.add_parameter("mult",label="Multiplier",default=1)
    def process_frame(self, frame):
        return frame*self.p["mult"]+self.p["shift"]




class FrameCutFilter(base.ISingleFrameFilter):
    """
    Filter that cuts out a part of the frame.
    """
    # _class_name="cut"  # class is only for illustration purposes
    _class_caption="Cut region"
    def setup(self):
        super().setup()
        self.add_parameter("x0",label="X start",kind="int",limit=(0,None))
        self.add_parameter("y0",label="Y start",kind="int",limit=(0,None))
        self.add_parameter("xsize",label="X size",kind="int",limit=(1,None),default=1)
        self.add_parameter("ysize",label="Y size",kind="int",limit=(1,None),default=1)
    def process_frame(self, frame):
        x0=min(self.p["x0"],frame.shape[1]-1)
        y0=min(self.p["y0"],frame.shape[0]-1)
        return frame[y0:y0+self.p["ysize"],x0:x0+self.p["xsize"]]




class BlockAverageFilter(base.IFrameFilter):
    """
    Filter that applies block average (averages frames in blocks of a given length).
    """
    # _class_name="block_avg"  # class is only for illustration purposes
    _class_caption="Block average"
    _class_description="Averages a given number of consecutive frames into a single frame. Frames are averaged in non-overlapping blocks."
    def setup(self):
        super().setup()
        self.setup_general(receive_all_frames=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=1)
        self.add_parameter("buff_accum",label="Accumulated frames",kind="int",indicator=True)
        self.buffer=[]
        self._bufflen=0
        self._latest_frame=None
    def receive_frames(self, frames):
        if self.buffer and self.buffer[0].shape!=frames.shape[1:]:
            self.buffer=[]
        self.buffer+=list(frames)
        self._bufflen=max(self._bufflen,min(len(self.buffer),self.p["length"]))
        if len(self.buffer)>self.p["length"]:
            nl=len(self.buffer)//self.p["length"]
            last_buffer=self.buffer[(nl-1)*self.p["length"]:nl*self.p["length"]]
            self.buffer=self.buffer[nl*self.p["length"]:]
            self._latest_frame=np.mean(last_buffer,axis=0)
        self.p["buff_accum"]=len(self.buffer)
    def generate_frame(self):
        if self._latest_frame is not None:
            result=self._latest_frame
            self._latest_frame=None
            self._bufflen=len(self.buffer)
            return result




class MovingAverageFilter(base.IMultiFrameFilter):
    """
    Filter that generates moving average (averages last ``self.p["length"]`` received frames).

    Identical to :class:`FastMovingAverageFilter` from ``builtin`` module, but a but slower;
    not used in the GUI, left for reference.
    """
    # _class_name="moving_avg"  # class is only for illustration purposes
    _class_caption="Moving average"
    _class_description="Averages a given number of consecutive frames into a single frame. Frames are averaged within a sliding window."
    def setup(self):
        super().setup(process_incomplete=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=20)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def process_buffer(self, buffer):
        if not buffer:
            return None
        return np.mean(buffer,axis=0)




class MovingAverageSubtractionFilter(base.IMultiFrameFilter):
    """
    Filter that generate moving average difference.

    Finds the difference between the average of the last ``self.p["length"]`` received frames and the average of the preceding ``self.p["length"]`` frames

    Identical to :class:`FastMovingAverageSubtractionFilter` from ``builtin`` module, but a but slower;
    not used in the GUI, left for reference.
    """
    # _class_name="moving_avg_sub" # class is only for illustration purposes
    _class_caption="Moving average subtract"
    _class_description=("Averages two consecutive frame blocks into two individual frames and takes their difference. "
        "Similar to running background subtraction, but with some additional time averaging.")
    def setup(self):
        super().setup()
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=20)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value*2 if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def process_buffer(self, buffer):
        return np.mean(buffer[0:self.p["length"]],axis=0)-np.mean(buffer[self.p["length"]:2*self.p["length"]],axis=0)
