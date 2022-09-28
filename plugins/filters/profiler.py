"""
Gaussian beam profiler filter.
"""


from . import base
from pylablib.core.dataproc import fitting

import numpy as np



class BeamProfileFilter(base.ISingleFrameFilter):
    """
    Beam profiler filter.
    """
    _class_name="beam_profile"
    _class_caption="Beam profile"
    _class_description="Beam profiler filter: averages image in strips of the given widths in vertical and horizontal directions, fits the resulting profiles to Gaussians and shows the widths"
    def setup(self):
        """Initial filter setup"""
        super().setup(multichannel="average")
        # Setup control parameters
        self.add_parameter("x_position",label="X position",kind="int",limit=(0,None))
        self.add_parameter("y_position",label="Y position",kind="int",limit=(0,None))
        self.add_parameter("track_lines",label="Use plot lines",kind="check")
        self.add_parameter("track_max",label="Locate maximum",kind="check")
        self.add_parameter("width",label="Averaging width",kind="int",limit=(1,None),default=10)
        self.add_parameter("show_map_info",label="Showing",kind="select",options={"frame":"Frame","data":"Data profile","fit":"Fit profile"})
        # Add width indicators
        self.add_parameter("x_fit_width",label="X width",kind="float",indicator=True)
        self.add_parameter("y_fit_width",label="Y width",kind="float",indicator=True)
        # Add auxiliary parameters
        self.add_linepos_parameter(default=None)  # indicate that the filter needs to get a cross position as "linepos" parameter
        self.add_rectangle("x_selection",(0,0),(0,0))  # add a rectangle indicating x-cut area
        self.add_rectangle("y_selection",(0,0),(0,0))  # add a rectangle indicating y-cut area
        self.select_plotter("frame")
    def set_parameter(self, name, value):  # called automatically any time a GUI parameter or an image cross position are changed
        """Set filter parameter with the given name"""
        super().set_parameter(name,value)  # default parameter set (store the value in ``self.p`` dictionary)
        if name in ["linepos","track_lines","show_map_info"] and self.p["show_map_info"]=="frame" and self.p["track_lines"] and self.p["linepos"]:
            self.set_parameter("x_position",int(self.p["linepos"][1]))
            self.set_parameter("y_position",int(self.p["linepos"][0]))
    def _get_region(self, shape):
        """Get the spans ``(start, stop)`` of the two averaging regions"""
        xp,yp,w=self.p["x_position"],self.p["y_position"],self.p["width"]
        def _get_rng(ax, p):
            start,stop=(p-w//2),(p-w//2+w)
            size=shape[ax]
            start=max(start,0)
            stop=min(stop,size)
            start=max(min(start,stop-w),0)
            stop=min(max(stop,w),size)
            return start,stop
        return _get_rng(0,yp),_get_rng(1,xp)
    def profile(self, xs, center, width, height, background):
        """Profile fit function"""
        return np.exp(-(xs-center)**2/(2*width**2))*height+background
    def fit_profile(self, cut):
        """
        Fit the beam profile.

        Return tuple ``(fit_parameters, fit_cut)``, where ``fit_parameters`` is a dictionary with the resulting fit parameters,
        and ``fit_cut`` is a fit to the given profile cut.
        """
        xs=np.arange(len(cut))
        fitter=fitting.Fitter(self.profile,"xs")
        background=np.median(cut)
        fit_parameters={"center":cut.argmax(),"width":len(cut)/10,"background":background,"height":cut.max()-background}
        fp,ff=fitter.fit(xs,cut,fit_parameters=fit_parameters)
        return fp,ff(xs)
    def process_frame(self, frame):  # called automatically whenver a new frame is received from the camera
        """Process a new camera frame"""
        if self.p["track_max"]:  # move center to the image maximum, if enabled
            imax,jmax=np.unravel_index(frame.argmax(),frame.shape)
            self.set_parameter("x_position",jmax)
            self.set_parameter("y_position",imax)
        # Extract profiles
        rs,cs=self._get_region(frame.shape)
        xcut=np.mean(frame[rs[0]:rs[1],:],axis=0)
        xcut/=xcut.max()
        ycut=np.mean(frame[:,cs[0]:cs[1]],axis=1)
        ycut/=ycut.max()
        # Fit profiles
        xfp,xfcut=self.fit_profile(xcut)
        self.p["x_fit_width"]=xfp["width"]
        yfp,yfcut=self.fit_profile(ycut)
        self.p["y_fit_width"]=yfp["width"]
        if self.p["show_map_info"]=="frame":  # showing the original frames
            rs,cs=self._get_region(frame.shape)
            nr,nc=frame.shape
            # Set parameters of the rectangles indicating the profile extraction areas
            self.change_rectangle("x_selection",center=((rs[1]+rs[0])/2,nc/2),size=(rs[1]-rs[0],nc),visible=True)
            self.change_rectangle("y_selection",center=(nr/2,(cs[1]+cs[0])/2),size=(nr,cs[1]-cs[0]),visible=True)
            self.select_plotter("frame")
            return frame
        if self.p["show_map_info"]=="data":  # showing the extracted profiles
            return xcut[None,:]*ycut[:,None]
        return xfcut[None,:]*yfcut[:,None]  # showing the fit profiles