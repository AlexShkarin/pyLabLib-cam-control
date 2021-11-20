from pylablib.core.gui import QtCore
from pylablib.core.gui.widgets import container, param_table
from pylablib.core.thread import controller
from pylablib.core.utils import dictionary

class ActivityIndicator_GUI(container.QWidgetContainer):
    """
    Activity indicator widget.

    Displays statuses of different processes based on the resource manager.
    """
    _ind_groups=["camera","saving","processing","misc"]
    _status_styles={"off":"",
                    "on":"background:lightgreen; color: black",
                    "pause":"background:green; color: black",
                    "warning":"background:gold; color: black",
                    "error":"background:red; color: black"}
    def setup(self, resource_manager_thread):
        super().setup(no_margins=True)
        self.setMinimumWidth(25)
        self.setMaximumWidth(25)
        self.resource_manager_thread=resource_manager_thread
        self.resource_manager=controller.sync_controller(self.resource_manager_thread)
        self.pinds={g:{} for g in self._ind_groups}
        # Setup GUI
        self.params=self.add_child("params",param_table.ParamTable(self))
        self.params.setup(add_indicator=False)
        self.params.get_sublayout().setContentsMargins(0,0,0,0)
        for g in self._ind_groups:
            self.params.add_sublayout(g,kind="vbox")
            self.params.add_spacer(10)
        self.params.add_padding(stretch=1)
        # Timer
        self.add_timer_event("update_pinds",self.update_pinds,period=0.5)
        self.ctl.add_thread_method("add_activity",self.add_activity)
        self.ctl.add_thread_method("update_activity_status",self.update_activity_status)
    def start(self):
        self.update_pinds()
        super().start()

    def add_activity(self, group, name, caption=None, short_cap=None, order=None, ctl=None):
        """Add a new activity indicator withing the given group and name"""
        self.resource_manager.cs.add_resource("process_activity",group+"/"+name,ctl=ctl,
            caption=caption,short_cap=short_cap,order=order)
        self.update_pinds()
    def update_activity_status(self, group, name, status):
        """Update an activity indicator status"""
        self.resource_manager.csi.update_resource("process_activity",group+"/"+name,status=status)
        self.set_pind(group,name,status)

    def _find_position(self, group, order=None):
        if order is None:
            order=max(self.pinds[group].values())
        if not isinstance(order,tuple):
            order=(order,)
        ordlist=sorted((o,n) for n,o in self.pinds[group].items())
        nxt=None
        for o,n in ordlist:
            if o>order:
                nxt=n
                break
        if nxt is None:
            return self.params.get_layout_shape(group)[0],order
        return self.params.get_element_position(self.params.w[group,nxt])[1][0],order
    def add_pind(self, group, name, caption=None, short_cap=None, order=None):
        """Add indicator to the table"""
        if caption is None:
            caption=name.capitalize()
        if short_cap is None:
            short_cap=caption[:3]
        g=self.pinds[group]
        if name in g:
            raise ValueError("process indicator {} already exists in group {}".format(name,group))
        pos,order=self._find_position(group,order)
        g[name]=order
        self.params.add_text_label((group+"/"+name),location=(group,pos),value=short_cap,tooltip=caption)
        widget=self.params.w[group,name]
        widget.setMinimumWidth(20)
        widget.setMinimumHeight(20)
        widget.setAlignment(QtCore.Qt.AlignCenter)
    def remove_pind(self, group, name):
        """Remove indicator from the table"""
        if name not in self.pinds[group]:
            raise KeyError("process indicator {} does not exist in group {}".format(name,group))
        del self.pinds[group][name]
        self.params.remove_widget((group,name))
    def set_pind(self, group, name, status):
        """Set indicator status"""
        if (group,name) in self.params.w:
            self.params.w[group,name].setStyleSheet(self._status_styles[status])

    def update_pinds(self):
        """Update GUI based on the specified resources"""
        pinds=self.resource_manager.cs.list_resources("process_activity")
        present=set()
        for i,d in pinds.items():
            path=dictionary.split_path(i)
            group,name=path[0],"/".join(path[1:])
            status=d.get("status","off")
            if name not in self.pinds[group]:
                self.add_pind(group,name,caption=d.get("caption"),short_cap=d.get("short_cap"),order=d.get("order"))
            self.set_pind(group,name,status)
            present.add((group,name))
        for g in self.pinds:
            for n in list(self.pinds[g]):
                if (g,n) not in present:
                    self.remove_pind(g,n)