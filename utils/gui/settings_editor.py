from pylablib.core.fileio import loadfile, savefile
from pylablib.core.gui import QtWidgets, QtCore
from pylablib.core.thread.controller import exsafe, exsafeSlot

from pylablib import widgets
import os


class SkipParameterError(ValueError):
    """Exception indicating that the parameter values should be skipped on saving"""
class SettingsEditor(widgets.QWidgetContainer):
    """
    Settings editor.

    Loads, displays, edits, and saves the preferences contained in the settings file.
    """
    def setup(self, main_frame):
        super().setup()
        self.setWindowTitle("Preferences")
        self.setWindowFlag(QtCore.Qt.Dialog)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint,False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint,False)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.main_frame=main_frame
        self.main_frame.closed.connect(self.close)
        self.settings_src=main_frame.settings["runtime/settings_src"]
        if os.path.exists(self.settings_src):
            self.settings=loadfile.load_dict(self.settings_src)
        else:
            QtWidgets.QMessageBox.critical(self,"Missing settings file","Could not find settings file: {}".format(self.settings_src),QtWidgets.QMessageBox.Ok)
            self.close()
            return False
        self.defined_settings={}
        self.tabs=self.add_child("tabs",widgets.QTabContainer(self))
        self.cam_tabs={}
        self.global_tab=self.tabs.add_tab("global","Global",widget=widgets.ParamTable(self))
        self.setup_settings(self.global_tab)
        for cam in self.settings.get("cameras",{}):
            name=self.settings.get(("cameras",cam,"display_name"),cam)
            self.cam_tabs[name]=self.tabs.add_tab("cam/"+cam,name,widget=widgets.ParamTable(self))
            self.cam_tabs[name].camera=cam
            self.setup_settings(self.cam_tabs[name])
        self.buttons=self.add_child("buttons",widgets.ParamTable(self))
        self.buttons.setup(add_indicator=False)
        with self.buttons.using_new_sublayout("buttons","hbox"):
            self.buttons.add_padding()
            self.buttons.add_button("save","Save")
            self.buttons.vs["save"].connect(self.save_close)
            self.buttons.add_button("cancel","Cancel")
            self.buttons.vs["cancel"].connect(self.close)
            for n in ["save","cancel"]:
                self.w[n].setFixedWidth(100)
        self.display_settings()
        self.hide()
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        return True
    
    @exsafeSlot()
    def save_close(self):
        """Save parameters and close the window"""
        savefile.save_dict(self.collect_settings(),self.settings_src)
        QtWidgets.QMessageBox.information(self,"Information","Restart the application for the changes to take effect",QtWidgets.QMessageBox.Ok)
        self.close()

    def decorate_parameter(self, table: widgets.ParamTable, name, default, descfunc=None):
        """Add parameter decoration: description label and (if necessary) enable checkbox"""
        vname="value/"+name
        table.add_text_label("desc/"+name,"",location=(-1,4,1,1))
        if descfunc is None:
            descfunc=table.h["value",name].repr_value
        @exsafe
        def display_desc(value):
            table.v["desc",name]=descfunc(value)
            if not hasattr(table,"camera"):
                for ct in self.cam_tabs.values():
                    ct.update_value(("enable",name))
        table.vs[vname].connect(display_desc)
        if hasattr(table,"camera"):
            if default is not None:
                table.add_check_box("enable/"+name,"",location=(-1,0,1,1))
                @exsafe
                def on_enable(value):
                    table.set_enabled(vname,value)
                    if value:
                        display_desc(table.v[vname])
                    else:
                        display_desc(self.global_tab.v[vname] if vname in self.global_tab else default)
                table.vs["enable",name].connect(on_enable)
                on_enable(False)
            else:
                display_desc(table.v[vname])
            if name.startswith("camera/"):
                pname="cameras/{}/{}".format(table.camera,name.split("/",1)[1])
            else:
                pname="css/{}/{}".format(table.camera,name)
            self.defined_settings[pname]=(table,name)
        else:
            w=QtWidgets.QCheckBox("",parent=table)  # dummy checkbox as a workaround for aligning tabs layouts
            p=w.sizePolicy()
            p.setRetainSizeWhenHidden(True)
            w.setSizePolicy(p)
            table.add_to_layout(w,location=(-1,0,1,1))
            w.hide()
            self.defined_settings[name]=(table,name)
            display_desc(table.v[vname])
    def add_bool_parameter(self, table: widgets.ParamTable, name, label, default=False, description=("Off","On")):
        """Add a boolean settings parameters"""
        table.add_check_box("value/"+name,"",value=default,label=label,location=("next",1,1,2))
        self.decorate_parameter(table,name,default=default,descfunc=lambda v: description[1 if v else 0])
    def add_choice_parameter(self, table: widgets.ParamTable, name, label, options, default=None, description=None):
        """Add a combobox settings parameters"""
        ovals,olabels=list(zip(*options.items()))
        if default is None:
            default=ovals[0]
        table.add_combo_box("value/"+name,value=default,label=label,options=olabels,index_values=ovals,location=("next",1,1,2))
        description=options if description is None else description
        self.decorate_parameter(table,name,default=default,descfunc=lambda v: description.get(v,v) if v!=-1 else "N/A")
    def add_integer_parameter(self, table: widgets.ParamTable, name, label, limits=(0,None), default=0):
        """Add an integer settings parameters"""
        table.add_num_edit("value/"+name,value=default,label=label,limiter=limits+("coerce","int"),formatter="int",location=("next",1,1,2))
        self.decorate_parameter(table,name,default=default)
    def add_string_parameter(self, table: widgets.ParamTable, name, label, default=""):
        """Add a string settings parameters"""
        table.add_text_edit("value/"+name,value=default,label=label,location=("next",1,1,2))
        self.decorate_parameter(table,name,default=default)
    def add_float_parameter(self, table: widgets.ParamTable, name, label, limits=(0,None), fmt=".1f", default=0):
        """Add a float settings parameters"""
        table.add_num_edit("value/"+name,value=default,label=label,limiter=limits,formatter=fmt,location=("next",1,1,2))
        self.decorate_parameter(table,name,default=default)

    def setup_settings(self, table: widgets.ParamTable):
        """Setup the settings table in the given widget"""
        table.setup(add_indicator=False)
        cam_table=hasattr(table,"camera")
        table.add_decoration_label("Override global" if cam_table else "",location=(0,0,1,2))
        table.add_spacer(0,30,location=(0,0,1,1))
        table.add_spacer(0,200,location=(0,1,1,1))
        table.add_spacer(0,150,location=(0,2,1,1))
        table.add_spacer(0,10,location=(0,3,1,1))
        table.add_spacer(0,250,location=(0,4,1,1))
        self.add_bool_parameter(table,"interface/compact","Compact interface")
        self.add_choice_parameter(table,"interface/color_theme","Color theme",{"standard":"Standard","dark":"Dark","light":"Light"},default="dark")
        self.add_bool_parameter(table,"interface/expandable_edits","Expandable text boxes",default=True)
        table.add_spacer(10)
        self.add_choice_parameter(table,"interface/datetime_path/file","Add date/time file method",{"pfx":"Prefix","sfx":"Suffix","folder":"Folder"},
            description={"pfx":"Add as a prefix","sfx":"Add as a suffix","folder":"Create separate folder"},default="sfx")
        self.add_choice_parameter(table,"interface/datetime_path/folder","Add date/time folder method",{"pfx":"Prefix","sfx":"Suffix","folder":"Folder"},
            description={"pfx":"Add as a prefix","sfx":"Add as a suffix","folder":"Create separate folder"},default="sfx")
        self.add_integer_parameter(table,"saving/max_queue_ram","Max saving buffer RAM (Mb)",limits=(512,None),default=4096)
        self.add_bool_parameter(table,"interface/popup_on_missing_frames","Popup on missing frames",default=True)
        table.add_spacer(10)
        self.add_choice_parameter(table,"frame_processing/status_line_policy","Status line display policy",
            {"keep":"Keep","cut":"Cut","zero":"Zero","median":"Median","duplicate":"Duplicate"},default="duplicate",
            description={"keep":"Keep unchanged","cut":"Cut row off","zero":"Set row to zero","median":"Set row to image median","duplicate":"Duplicate previous row"})
        self.add_choice_parameter(table,"interface/cam_control/roi_kind","ROI entry method",{"minmax":"Min-Max","minsize":"Min-Size","centersize":"Center-Size"},
            description={"minmax":"Minimal and maximal coordinates","minsize":"Minimal coordinates and size","centersize":"Center coordinates and size"},default="minmax")
        if cam_table:
            table.add_spacer(10)
            self.add_string_parameter(table,"camera/display_name","Camera name",default=None)
            self.add_integer_parameter(table,"camera/params/misc/buffer/min_size/frames","Frame buffer (frames)",
                limits=(50,None),default=100)
            self.add_float_parameter(table,"camera/params/misc/buffer/min_size/time","Frame buffer (s)",
                limits=(0.2,None),default=1.0)
            self.add_float_parameter(table,"camera/params/misc/loop/min_poll_period","Poll period (s)",
                limits=(0.01,1),default=0.05,fmt=".2f")
        table.set_column_stretch([0,0,0,0,1])
        table.add_padding(kind="vertical",location=("next",1,1,1),stretch=1)

    def get_displayed_parameter(self, name, value):
        """Convert settings file parameter value into the GUI parameter value"""
        if name=="saving/max_queue_ram":
            return max(value//2**20,1)
        return value
    def get_stored_parameter(self, name, value):
        """Convert GUI parameter value into the settings file parameter value"""
        if name=="saving/max_queue_ram":
            return value*2**20
        if name.startswith("interface/datetime_path/") and value==-1:
            raise SkipParameterError
        return value
    def display_settings(self):
        """Display settings in the GUI"""
        for k,par in self.defined_settings.items():
            table,name=par
            if k in self.settings:
                if ("enable",name) in table:
                    table.v["enable",name]=True
                table.v["value",name]=self.get_displayed_parameter(name,self.settings[k])
    def collect_settings(self):
        """Collect settings within the GUI and return their dictionary"""
        settings=self.settings.copy()
        for k,par in self.defined_settings.items():
            table,name=par
            try:
                value=self.get_stored_parameter(name,table.v["value",name])
                if ("enable",name) in table:
                    if table.v["enable",name]:
                        settings[k]=value
                    elif k in settings:
                        del settings[k]
                else:
                    settings[k]=value
            except SkipParameterError:
                pass
        return settings