from pylablib.core.utils import dictionary


class ICameraDescriptor:
    """
    Base camera descriptor.

    Includes method to detect cameras of the given type, start threads, and create GUI (settings control and status display).
    """
    _cam_kind=None
    def __init__(self, name, settings=None):
        self.name=name
        self.settings=settings or {}
    
    @classmethod
    def build_cam_desc(cls, params):
        return dictionary.Dictionary({"kind":cls._cam_kind,"params":params or {}})
    @classmethod
    def print_added_camera(cls, name, desc):
        """Print information about a newly detected camera"""
        print("Adding camera under name {}:".format(name))
        print("\tkind = '{}'".format(desc["kind"]))
        if "params" in desc:
            print("\tparams = '{}'".format(desc["params"].as_dict()))
        if "display_name" in desc:
            print("\tdisplay_name = '{}'".format(desc["display_name"]))
        print("")
    @classmethod
    def detect(cls, verbose=False):
        """Detect all cameras of the given type"""
        raise NotImplementedError
    def get_kind_name(self):
        """Get user-friendly name to be displayed in the GUI"""
        raise NotImplementedError
    def get_camera_labels(self):
        """Get label ``(kind_name, cam_name)``"""
        return self.get_kind_name(),self.settings.get("display_name",self.name)

    def make_thread(self, name):
        """Create camera thread with the given name"""
        raise NotImplementedError

    def make_gui_control(self, parent):
        """Create GUI settings control with the given parent widget"""
        raise NotImplementedError
    def make_gui_status(self, parent):
        """Create GUI status table with the given parent widget"""
        raise NotImplementedError