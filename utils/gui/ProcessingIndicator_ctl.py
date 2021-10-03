from pylablib.core.gui.widgets import param_table
from pylablib.core.thread import controller


class ProcessingIndicator_GUI(param_table.ParamTable):
    """
    Processing steps display above the plot windows.

    Shows and controls display FPS, and notifies if a slowdown is active.

    Args:
        items: a list of step items ``[(name,(caption,getter))]``, where ``name`` is the item name,
            ``caption`` is its caption (shown in the steps table),
            and ``getter`` is a function which returns a string with the step representation or ``None`` if the step is disabled.
        update: if ``True``, update indicators right after setup.
    """
    def setup(self, items, update=True):
        super().setup(add_indicator=False)
        self.items=items
        for name,(caption,_) in items:
            with self.using_new_sublayout(name,"hbox"):
                self.add_text_label(name,label="{}:  ".format(caption))
                self.add_padding()
        if update:
            self.update_indicators()
        self._ignore_set_values={name for name,_ in items}
    def _set_value(self, name, value, default="none"):
        self.w[name].setStyleSheet(None if value is None else "font-weight: bold")
        self.v[name]=default if value is None else value
    @controller.exsafe
    def update_indicators(self):
        """Update processing step indicators"""
        for name,(_,getter) in self.items:
            self._set_value(name,getter())



def binning_item(preprocessor):
    """Create an processing step item based on a binning thread"""
    ctl=controller.sync_controller(preprocessor)
    def getter():
        params=ctl.v["params"]
        if ctl.v["enabled"]:
            spat_bin="{}x{} spatial".format(*params["spat/bin"]) if params["spat/bin"]!=(1,1) else ""
            temp_bin="{} temporal".format(params["time/bin"]) if params["time/bin"]!=1 else ""
            if spat_bin or temp_bin:
                return ", ".join([i for i in [spat_bin,temp_bin] if i])
        return None
    return "Binning",getter

def background_item(processor):
    """Create an processing step item based on a background subtraction thread thread"""
    ctl=controller.sync_controller(processor)
    def getter():
        if ctl.v["enabled"]:
            method=ctl.v["method"]
            if method=="snapshot" and ctl.v["snapshot/background/state"]!="valid":
                return None
            if method=="running" and ctl.v["running/background/frame"] is None:
                return None
            return method.capitalize()
        return None
    return "Background subtraction",getter