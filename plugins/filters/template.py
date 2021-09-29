"""
Example template module for custom-defined filters.
"""


from . import base

import numpy as np
import scipy.ndimage



class TemplateSingleFrameFilter(base.ISingleFrameFilter):
    """
    Template filter which does nothing.
    """
    # _class_name="template"  # NOTE: uncomment this line to enable the filter
    _class_caption="Template single-frame filter"
    _class_description="This is a template single-frame filter, which is equivalent to the standard Gaussian blur filter"
    def setup(self):
        super().setup()
        self.add_parameter("width",label="Width",limit=(0,None),default=2)
    def process_frame(self, frame):
        return scipy.ndimage.gaussian_filter(frame.astype("float"),self.p["width"])



class TemplateMultiFrameFilter(base.IMultiFrameFilter):
    """
    Template filter which does nothing.
    """
    # _class_name="template"  # NOTE: uncomment this line to enable the filter
    _class_caption="Template multi-frame filter"
    _class_description="This is a template multi-frame filter, which simply returns the average of all frames"
    def setup(self):
        super().setup(buffer_size=10,process_incomplete=True) # set number of frames to 10 by default
        self.add_parameter("length",label="Number of frames",kind="int",limit=(1,None),default=self.buffer_size)
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