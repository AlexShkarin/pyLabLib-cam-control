try:
    from PyQt5 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

import os
import sys
import ctypes

if __name__=="__main__":
    startdir=os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
    sys.path.append(os.path.abspath("."))  # set current folder to the file location and add it to the search path

from utils import version


def prepare_app():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling,True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps,True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_Use96Dpi,True)
    return QtWidgets.QApplication([])

class SplashScreen(QtWidgets.QSplashScreen):
    """
    Splash screen widget.

    Shows logo, message, and version label.
    """
    def __init__(self):
        pixmap=QtGui.QPixmap("./splash.png")
        super().__init__(pixmap)
        self.setObjectName("camControlSplash")
        self.current_style=QtCore.QCoreApplication.instance().style()
        self.setStyle(self.current_style)
        self.current_font=self.font()
        self.current_font.setPixelSize(16)
        self.setFont(self.current_font)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.setLayout(QtWidgets.QVBoxLayout(self))
        self.layout().addItem(QtWidgets.QSpacerItem(1,1,QtWidgets.QSizePolicy.MinimumExpanding,QtWidgets.QSizePolicy.MinimumExpanding))
        self.layout().setContentsMargins(5,5,5,5)
        self.vlabel=QtWidgets.QLabel(self)
        self.vlabel.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignBottom)
        self.vlabel.setText("PyLabLib cam-control\nVersion {}".format(version))
        self.vlabel.setStyle(self.current_style)
        self.layout().addWidget(self.vlabel)
        self.vlabel.setFont(self.current_font)
    def show_message(self, text):
        self.showMessage(text,QtCore.Qt.AlignLeft|QtCore.Qt.AlignBottom)

def get_splash_screen(name="camControlSplash"):
    """Get splash screen if present"""
    widgets=QtCore.QCoreApplication.instance().topLevelWidgets()
    for w in widgets:
        if w.objectName()==name:
            return w
def update_splash_screen(show=None, msg=None):
    """Show or hide splash screen and / or change its message"""
    splash=get_splash_screen()
    if splash is not None:
        if show is True:
            splash.show()
        elif show is False:
            splash.hide()
        if msg is not None:
            splash.show_message(msg)

if __name__=="__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'cam-control')  # fixes taskbar icon issue
    app=prepare_app()
    splash=SplashScreen()
    splash.show_message("Setting up the environment...")
    splash.show()
    app.processEvents()
    # Minimize/maximize to bring the window to the front
    splash.showMinimized()
    app.processEvents()
    splash.setWindowState(splash.windowState()&~QtCore.Qt.WindowMinimized)
    app.processEvents()

    import control
    control.execute(app)
    
    os.chdir(startdir)