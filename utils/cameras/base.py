from pylablib.core.utils import dictionary

import traceback
import sys


class ICameraDescriptor:
    """
    Base camera descriptor.

    Includes method to detect cameras of the given type, start threads, and create GUI (settings control and status display).
    """
    _cam_kind=None
    _expands=None
    def __init__(self, name, settings=None):
        self.name=name
        self.settings=settings or {}
    
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
    def print_skipped_camera(cls):
        """Print information about a skipped camera"""
        print("Skipping the camera\n")
    @classmethod
    def print_error(cls):
        """Print an exception traceback"""
        traceback.print_exc()
        print("",file=sys.stderr)
    @classmethod
    def iterate_cameras(cls, verbose=False):
        """Iterate over all cameras of the given type"""
        raise NotImplementedError
    @classmethod
    def generate_description(cls, idx, cam=None, info=None):
        """
        Return camera description dictionary for the given camera index, camera class, and additional info.
        
        Return either tuple ``(cam_name, cam_desc)`` or ``None`` (camera can not be added).
        """

    @classmethod
    def build_cam_desc(cls, params, cam_kind=None):
        return dictionary.Dictionary({"kind":cam_kind or cls._cam_kind,"params":params or {}})
    @classmethod
    def can_expand(cls, cam_kind):
        return cls._expands==cam_kind
    @classmethod
    def find_description(cls, idx, cam=None, info=None, camera_descriptors=None):
        """
        Find the most specific description for the given camera index, camera class, and additional info.

        Return tuple ``(cls, desc)``, where ``desc`` is the result of :meth:`generate_description` call
        and ``cls`` is the class which generated this description.
        """
        desc=cls.generate_description(idx,cam=cam,info=info)
        if desc and camera_descriptors:
            for d in camera_descriptors:
                if d.can_expand(cls._cam_kind):
                    exp_cls,exp_desc=d.find_description(idx,cam=cam,info=info,camera_descriptors=camera_descriptors)
                    if exp_desc is not None:
                        return exp_cls,exp_desc
        return cls,desc
    @classmethod
    def detect(cls, verbose=False, camera_descriptors=None):
        """Detect all cameras of the given type"""
        cameras=dictionary.Dictionary()
        for i,(cam,info) in enumerate(cls.iterate_cameras(verbose=verbose)):
            desc_cls,desc=cls.find_description(i,cam=cam,info=info,camera_descriptors=camera_descriptors)
            if desc is not None and desc[0] is not None:
                if verbose: desc_cls.print_added_camera(*desc)
                cameras[desc[0]]=desc[1]
            else:
                if verbose: desc_cls.print_skipped_camera()
        return cameras
    def get_kind_name(self):
        """Get user-friendly name to be displayed in the GUI"""
        raise NotImplementedError
    def get_camera_labels(self):
        """Get label ``(kind_name, cam_name)``"""
        return self.get_kind_name(),self.settings.get("display_name",self.name)
    @classmethod
    def get_class_settings(cls):
        """Get dictionary with generic class settings"""
        return {"allow_garbage_collection":True}

    def make_thread(self, name):
        """Create camera thread with the given name"""
        raise NotImplementedError

    def make_gui_control(self, parent):
        """Create GUI settings control with the given parent widget"""
        raise NotImplementedError
    def make_gui_status(self, parent):
        """Create GUI status table with the given parent widget"""
        raise NotImplementedError