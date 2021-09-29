"""
Module contained basic built-in filters.
"""

import numpy as np
import scipy.ndimage
import numba as nb

from . import base





class GaussianBlurFilter(base.ISingleFrameFilter):
    """
    Filter that applies Gaussian blur with the specified width.
    """
    _class_name="blur"
    _class_caption="Gaussian blur"
    _class_description="Standard convolution Gaussian blur filter"
    def setup(self):
        super().setup()
        self.add_parameter("width",label="Width",limit=(0,None),default=2)
    def process_frame(self, frame):
        return scipy.ndimage.gaussian_filter(frame.astype("float"),self.p["width"])






class FFTBandpassFilter(base.ISingleFrameFilter):
    """
    Filter that applies Fourier domain bandpass filter (either hard mask, or difference of Gaussians).
    """
    _class_name="fft_bandpass"
    _class_caption="FFT bandpass"
    _class_description=("High- and low-pass filter operating in Fourier domain. Filters out variations below minimal width and above maximal width. "
        "Uses either a hard cutoff, or a smooth Gaussian cutoff, which is identical to the Gaussian blur.")
    def setup(self):
        super().setup()
        self.add_parameter("minwidth",label="Minimal width",limit=(0,None),default=2)
        self.add_parameter("maxwidth",label="Maximal width",limit=(0,None),default=10)
        self.add_parameter("filter_kind",label="Filter kind",kind="select",options={"smooth":"Smooth (DoG)","hard":"Hard"})
        self.add_parameter("show_info",label="Showing",kind="select",options={"frame":"Filtered frame","psd":"Raw PSD","filt_psd":"Filtered PSD","filt":"Filter"})
        self.mask=None
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        if self.p["minwidth"]>self.p["maxwidth"]:
            self.p["minwidth"],self.p["maxwidth"]=self.p["maxwidth"],self.p["minwidth"]
        self._update_mask()
    def _update_mask(self, shape=None):
        if shape is None:
            if self.mask is None:
                return
            shape=self.mask.shape
        xf=np.fft.fftfreq(shape[0])*2*np.pi
        yf=np.fft.fftfreq(shape[1])*2*np.pi
        xfm,yfm=np.meshgrid(xf,yf,indexing="ij")
        rsq=xfm**2+yfm**2
        if self.p["filter_kind"]=="hard":
            self.mask=((rsq*self.p["maxwidth"]**2>1)&(rsq*self.p["minwidth"]**2<1)).astype("float")
        else:
            self.mask=np.exp(-rsq*self.p["minwidth"]**2/2.)-np.exp(-rsq*self.p["maxwidth"]**2/2.)
    def _apply_mask(self, frame):
        frame_ft=np.fft.fft2(frame)
        return np.fft.ifft2(frame_ft*self.mask).real
    def _get_aux_info(self, frame):
        if self.p["show_info"] in ["psd","filt_psd"]:
            frame_ft=np.fft.fft2(frame)/np.prod(frame.shape)
            frame_ft[0,0]=0
            if self.p["show_info"]=="filt_psd": # filtered PSD
                frame_ft*=self.mask
            frame_PSD=np.abs(np.fft.fftshift(frame_ft))**2
            return frame_PSD
        return np.abs(np.fft.fftshift(self.mask))**2
    def process_frame(self, frame):
        if self.mask is None or self.mask.shape!=frame.shape:
            self._update_mask(frame.shape)
        if self.p["show_info"]=="frame":
            return self._apply_mask(frame)
        else:
            return self._get_aux_info(frame)




_movavg_per=4 # "manual" loop unrolling (parallel mode is unstable, shouldn't be used)
@nb.njit(fastmath=True,parallel=False,nogil=True) # buffer is guranteed to stay constant during execution, so can lift GIL; parallel mode is unstable, shouldn't be used
def _movavg(buffer):
    n,r,c=buffer.shape
    l=n//_movavg_per
    result=np.zeros((r,c),dtype=nb.float64)
    for k in range(l):
        for i in range(r):
            for j in range(c):
                for sk in range(_movavg_per):
                    result[i,j]+=buffer[k*_movavg_per+sk][i,j]
    for k in range(l*_movavg_per,n):
        for i in range(r):
            for j in range(c):
                result[i,j]+=buffer[k][i,j]
    return result/n
class FastMovingAverageFilter(base.IRingMultiFrameFilter):
    """
    Filter that generates moving average (averages last ``self.p["length"]`` received frames)

    Faster version of :class:`MovingAverageFilter`.
    """
    _class_name="moving_avg"
    _class_caption="Moving average"
    _class_description="Averages a given number of consecutive frames into a single frame. Frames are averaged within a sliding window."
    def setup(self):
        super().setup(buffer_size=20,process_incomplete=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=self.buffer_size)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def process_buffer(self, buffer, start, filled):
        if not filled:
            return None
        return _movavg(buffer[:filled])



class MovingAccumulatorFilter(base.IMultiFrameFilter):
    """
    Filter that does per-pixel accumulation of several frames in a row.

    Extension of :class:`MovingAverageFilter` (identical when ``self.p["kind"]=="mean"``).
    """
    _class_name="moving_acc"
    _class_caption="Moving accumulator"
    _class_description="Combine a given number of consecutive frames into a single frame using the given method. Frames are combined within a sliding window."
    def setup(self):
        super().setup(buffer_size=20,process_incomplete=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=self.buffer_size)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
        self.add_parameter("kind",label="Combination method",kind="select",options={"mean":"Mean","median":"Median","min":"Min","max":"Max","std":"Standard deviation"})
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def process_buffer(self, buffer):
        if not buffer:
            return None
        if self.p["kind"]=="mean":
            return np.mean(buffer,axis=0)
        if self.p["kind"]=="median":
            return np.median(buffer,axis=0)
        if self.p["kind"]=="min":
            return np.min(buffer,axis=0)
        if self.p["kind"]=="max":
            return np.max(buffer,axis=0)
        if self.p["kind"]=="std":
            return np.std(buffer,axis=0)


@nb.njit(fastmath=True,parallel=False,nogil=True) # buffer is guranteed to stay constant during execution, so can lift GIL; parallel mode is unstable, shouldn't be used
def _movavgsub(buffer, start=0):
    n,r,c=buffer.shape
    l=n//2
    result=np.zeros((r,c),dtype=nb.float64)
    for k in range(l):
        pk=(k+start)%n
        nk=(k+start+l)%n
        for i in range(r):
            for j in range(c):
                result[i,j]+=buffer[pk][i,j]
                result[i,j]-=buffer[nk][i,j]
    return result/l
class FastMovingAverageSubtractionFilter(base.IRingMultiFrameFilter):
    """
    Filter that generate moving average difference.

    Finds the difference between the average of the last ``self.p["length"]`` received frames and the average of the preceding ``self.p["length"]`` frames.

    Faster version of :class:`MovingAverageSubtractionFilter`.
    """
    _class_name="moving_avg_sub"
    _class_caption="Moving average subtract"
    _class_description=("Averages two consecutive frame blocks into two individual frames and takes their difference. "
        "Similar to running background subtraction, but with some additional time averaging.")
    def setup(self):
        super().setup(buffer_size=40)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=self.buffer_size//2)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value*2 if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def process_buffer(self, buffer, start, filled):
        return _movavgsub(buffer,start)



class TimeMapFilter(base.IMultiFrameFilter):
    """
    A filter which plots a time dependence of a line cut.
    """
    _class_name="time_map"
    _class_caption="Time map"
    _class_description=("Plots a time dependence of a line cut as a 2D map. "
    "A cut can be taken in either direction and, possibly, averaged over a band with the given width")
    def setup(self):
        super().setup(buffer_size=20,process_incomplete=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=self.buffer_size)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
        self.add_parameter("orientation",label="Orientation",kind="select",options={"rows":"Rows","cols":"Columns"})
        self.add_parameter("position",label="Position",kind="int",limit=(0,None))
        self.add_parameter("width",label="Width",kind="int",limit=(1,None),default=10)
        self.add_parameter("show_map_info",label="Showing",kind="select",options={"map":"Time map","frame":"Frame"})
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def _get_region(self, shape):
        p,w=self.p["position"],self.p["width"]
        axis=0 if self.p["orientation"]=="rows" else 1
        start,stop=(p-w//2),(p-w//2+w)
        size=shape[axis]
        start=max(start,0)
        stop=min(stop,size)
        start=max(min(start,stop-w),0)
        stop=min(max(stop,w),size)
        if axis==0:
            return axis,(start,stop),(0,shape[1])
        else:
            return axis,(0,shape[0]),(start,stop)
    def process_buffer(self, buffer):
        if not buffer:
            return None
        if self.p["show_map_info"]=="frame":
            frame=buffer[-1]
            _,rs,cs=self._get_region(frame.shape)
            out_frame=np.full(frame.shape,np.nan)
            cutout=frame[rs[0]:rs[1],cs[0]:cs[1]]
            out_frame[rs[0]:rs[1],cs[0]:cs[1]]=cutout
            return out_frame
        axis,rs,cs=self._get_region(buffer[0].shape)
        img=np.full((self.p["length"],buffer[0].shape[1-axis]),np.nan)
        img[:len(buffer)]=np.mean(np.array(buffer)[:,rs[0]:rs[1],cs[0]:cs[1]],axis=axis+1)
        return img



class DifferenceMatrixFilter(base.IMultiFrameFilter):
    """
    A filter which generated a matrix plot with the RMS differences between different frames.
    """
    _class_name="diff_matrix"
    _class_caption="Difference matrix"
    _class_description="Plots a 2D map showing RMS differences between different frames."
    def setup(self):
        super().setup(buffer_size=20,process_incomplete=True)
        self.add_parameter("length",label="Number of frames",kind="int",limit=(2,None),default=self.buffer_size)
        self.add_parameter("period",label="Frame step",kind="int",limit=(1,None),default=1)
    def set_parameter(self, name, value):
        super().set_parameter(name,value)
        buffer_size=value if name=="length" else None
        buffer_step=value if name=="period" else None
        self.reshape_buffer(buffer_size,buffer_step)
    def _calc_matrix(self, buffer):
        buffer=np.asarray(buffer,dtype=float).reshape((len(buffer),-1))
        sqs=np.sum(buffer**2,axis=1)
        sqss=sqs[:,None]+sqs[None,:]
        prods=np.tensordot(buffer,buffer.T,axes=1)
        return (sqss-2*prods)/buffer.shape[1]
    def process_buffer(self, buffer):
        if len(buffer)<2:
            return None
        img=np.full((self.p["length"],self.p["length"]),np.nan)
        img[:len(buffer),:len(buffer)]=self._calc_matrix(buffer)
        np.fill_diagonal(img,np.nan)
        return img