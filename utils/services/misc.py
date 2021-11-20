from pylablib.core.thread import controller
from pylablib.core.utils import dictionary
import threading


class SettingsManager(controller.QTaskThread):
    """
    Settings manager.
    
    Keeps track of all the settings sources (each settings source can add more of them),
    usually in order to save them when the data is being saved.
    """
    def setup_task(self):
        self.sources={}
        self.settings={}
        self.add_command("add_source")
        self.add_command("update_settings")
        self.add_command("get_all_settings")

    def add_source(self, name, func):
        """Add settings source as a function (called when settings values are requested)"""
        self.sources[name]=func
    def update_settings(self, name, settings):
        """Add settings values directly"""
        self.settings[name]=settings
    
    def get_all_settings(self, include=None, exclude=None, alias=None):
        """
        Get all settings values
        
        If `include` is not ``None``, it specifies a list of setting sources to include (by default, all sources).
        If `exclude` is not ``None``, it specifies a list of setting sources to exclude (by default, none are excluded).
        If `alias` is not ``None``, specifies aliases (i.e., different names in the resulting dictionary) for settings nodes.
        """
        settings=dictionary.Dictionary()
        alias=alias or {}
        for s in self.sources:
            if ((include is None) or (s in include)) and ((exclude is None) or (s not in exclude)):
                sett=self.sources[s]()
                settings.update({alias.get(s,s):sett})
        for s in self.settings:
            if ((include is None) or (s in include)) and ((exclude is None) or (s not in exclude)) and (s not in settings):
                sett=self.settings[s]
                settings.update({alias.get(s,s):sett})
        return settings




class ResourceManager(controller.QTaskThread):
    """
    Thread which manages information about broadly defined resources.

    Can add, get, update, or remove information about resources of different kind.

    Commands:
        - ``add_resource``: add a resource information
        - ``get_resource``: get values of a resource
        - ``list_resources``: get all resources of a given kind
        - ``update_resource``: update value of an already created resource
        - ``remove_resource``: remove the resource information
    """
    def setup_task(self):
        super().setup_task()
        self._lock=threading.Lock()
        self.resources={}
        self._updaters={}
        self.add_direct_call_command("add_resource")
        self.add_direct_call_command("get_resource")
        self.add_direct_call_command("list_resources")
        self.add_direct_call_command("update_resource")
        self.add_direct_call_command("add_multicast_updater")
        self.add_direct_call_command("remove_resource")
    
    def add_resource(self, kind, name, ctl=None, **kwargs):
        """
        Add a resource with the given kind and name.

        If `ctl` is not ``None``, can specify a resource-owning thread controller;
        if the controller is closed, the resource is automatically removed.
        `kwargs` specify the initial values of the resource.
        """
        with self._lock:
            if kind not in self.resources:
                self.resources[kind]={}
            if name in self.resources[kind]:
                raise ValueError("resource {}/{} already exists".format(kind,name))
            self.resources[kind][name]=kwargs
            if ctl is not None:
                ctl.add_stop_notifier(lambda: self.remove_resource(kind,name))
            value=kwargs.copy()
            self.send_multicast(tag="resource/added",value=(kind,name,value))
            self.send_multicast(tag="resource/{}/added".format(kind),value=(name,value))
    def get_resource(self, kind, name, default=None):
        """
        Get value of the resource with the given kind and name.

        If kind or name are not present, return `default`.
        """
        with self._lock:
            if kind in self.resources and name in self.resources[kind]:
                return self.resources[kind][name]
        return default
    def list_resources(self, kind):
        """
        List all resources of the given kind.

        Return a dictionary ``{kind: value}`` for all the resources.
        """
        with self._lock:
            return {k:v.copy() for k,v in self.resources.get(kind,{}).items()}
    def update_resource(self, kind, name, **kwargs):
        """
        Update value of the resource with the given kind and name.

        `kwargs` specify the values which need to be changed.
        """
        with self._lock:
            if kind in self.resources and name in self.resources[kind]:
                self.resources[kind][name].update(kwargs)
                value=self.resources[kind][name].copy()
                self.send_multicast(tag="resource/updated",value=(kind,name,value))
                self.send_multicast(tag="resource/{}/updated".format(kind),value=(name,value))
    def add_multicast_updater(self, kind, name, updater, srcs="any", tags=None, dsts="any"):
        """
        Add auto-updater which updates a resource based on an incoming multicast.

        `updater` is a function which takes 3 arguments (``src``, ``tag``, and ``value``)
        and returns an update dictionary (or ``None`` if no update is necessary).
        """
        def do_update(src, tag, value):
            params=updater(src,tag,value) or {}
            self.update_resource(kind,name,**params)
        sid=self.subscribe_direct(do_update,srcs=srcs,tags=tags,dsts=dsts)
        self._updaters.setdefault(kind,{}).setdefault(name,[]).append(sid)
    def remove_resource(self, kind, name):
        """Remove the resource with the given kind and name"""
        with self._lock:
            if kind in self.resources and name in self.resources[kind]:
                del self.resources[kind][name]
                self.send_multicast(tag="resource/removed",value=(kind,name))
                self.send_multicast(tag="resource/{}/removed".format(kind),value=name)
                if kind in self._updaters and name in self._updaters[kind]:
                    sids=self._updaters[kind].pop(name)
                    for s in sids:
                        self.unsubscribe(s)