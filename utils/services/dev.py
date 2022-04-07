from pylablib.core.gui import utils as gui_utils, QtCore

import os

def crop(img, left=0, right=None, top=0, bottom=None):
    """Crop QPixmap to the given rectangle"""
    w,h=img.size().width(),img.size().height()
    left=left%w
    right=right%w if right is not None else w
    top=top%h
    bottom=bottom%h if bottom is not None else h
    rect=QtCore.QRect(left,top,right-left,bottom-top)
    return img.copy(rect)
def take_screenshots(src):
    """Take screenshots for the documentation"""
    sfolder="screenshots/"
    os.makedirs(sfolder,exist_ok=True)
    if src.compact_interface:
        gui_utils.get_screenshot(src).save(sfolder+"overview_compact.png")
    else:
        gui_utils.get_screenshot(src).save(sfolder+"overview.png")
        src.c["plot_tabs"].set_by_name("standard_frame")
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(widget=src.c["plot_tabs"]).save(sfolder+"interface_image_display.png")
        gui_utils.get_screenshot(widget=src.c["params_loading_settings"]).save(sfolder+"interface_footer.png")
        src.c["control_tabs"].set_by_name("cam_tab")
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(widget=src.c["cam_controller/settings"].parentWidget(),border=(17,17,38,3)).save(sfolder+"interface_camera_settings.png")
        gui_utils.get_screenshot(widget=src.c["cam_controller/camstat"]).save(sfolder+"interface_camera_status.png")
        gui_utils.get_screenshot(widget=src.c["cam_controller/savebox"],border=(3,2)).save(sfolder+"interface_save_control.png")
        gui_utils.get_screenshot(widget=src.c["cam_controller/savestat"]).save(sfolder+"interface_save_status.png")
        src.c["control_tabs"].set_by_name("proc_tab")
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(widget=src.c["control_tabs/proc_tab"]).save(sfolder+"interface_processing.png")
        src.c["control_tabs"].set_by_name("proc_tab")
        src.ctl.sleep(0.1)
        crop(gui_utils.get_screenshot(widget=src.c["control_tabs/proc_tab"],border=(9,9,29,3)),bottom=540).save(sfolder+"interface_processing.png")
        src.v["plotting/enable"]=True
        src.ctl.sleep(0.1)
        crop(gui_utils.get_screenshot(widget=src.c["control_tabs/proc_tab"]),top=512,bottom=810).save(sfolder+"interface_time_plot.png")
        src.v["plotting/enable"]=False
        src.ctl.sleep(0.1)
        crop(gui_utils.get_screenshot(widget=src.c["activity_indicator"],border=3),bottom=195).save(sfolder+"interface_activity.png")
        src.c["control_tabs"].set_by_name("filter.filt/ctl_tab")
        src.ctl.sleep(0.1)
        crop(gui_utils.get_screenshot(widget=src.c["control_tabs/filter.filt/ctl_tab"],border=(9,9,29,3)),bottom=332).save(sfolder+"interface_filter.png")
        src.c["control_tabs"].set_by_name("plugins")
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(widget=src.c["control_tabs/plugins/trigger_save.trigsave/params"],border=(9,9,29,3)).save(sfolder+"interface_save_trigger.png")
        src.call_extra("settings_editor")
        src.settings_editor.tabs.setCurrentIndex(1)
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(window=src.settings_editor).save(sfolder+"interface_preferences.png")
        src.settings_editor.close()
        src.call_extra("tutorial")
        src.ctl.sleep(0.1)
        gui_utils.get_screenshot(window=src.tutorial_box).save(sfolder+"interface_tutorial.png")
        src.tutorial_box.close()
        if "show_attributes_window" in src.c["cam_controller/settings"].advanced_params:
            window=src.c["cam_controller/settings"].advanced_params.c["attributes_window"]
            window.show()
            window.tabs.set_by_name("value")
            src.ctl.sleep(0.1)
            gui_utils.get_screenshot(window=window).save(sfolder+"interface_camera_attributes.png")
            window.tabs.set_by_name("value_props")
            src.ctl.sleep(0.1)
            gui_utils.get_screenshot(window=window).save(sfolder+"interface_camera_attributes_settings.png")
            src.tutorial_box.close()

def on_key_press(src, event):
    """Execute dev functions based on the pressed keys"""
    if event.modifiers()&QtCore.Qt.ControlModifier and event.modifiers()&QtCore.Qt.ShiftModifier and event.key()==QtCore.Qt.Key_S:
        take_screenshots(src)