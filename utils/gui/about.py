from pylablib.core.gui import QtCore, QtWidgets
from pylablib import widgets
from .. import version


class AboutBox(widgets.QFrameContainer):
    """Window with the 'About' info"""
    def _increase_font(self, widget, factor):
        font=widget.font()
        font.setPointSize(int(font.pointSize()*factor))
        widget.setFont(font)
    def setup(self):
        super().setup()
        self.setWindowTitle("About")
        self.setWindowFlag(QtCore.Qt.Dialog)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint,False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint,False)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self._increase_font(self.add_decoration_label("PyLabLib cam-control"),1.6)
        self._increase_font(self.add_decoration_label("Version {}".format(version)),1.3)
        self.add_spacer(10)
        with self.using_new_sublayout("links","grid"):
            self.add_decoration_label("Documentation")
            link="https://pylablib-cam-control.readthedocs.io/"
            self.add_decoration_label("<a href='{link:}'>{link:}</a>".format(link=link),location=(-1,1)).setOpenExternalLinks(True)
            self.add_decoration_label("Report problems")
            link="https://github.com/AlexShkarin/pyLabLib-cam-control/issues"
            self.add_decoration_label("<a href='{link:}'>{link:}</a>".format(link=link),location=(-1,1)).setOpenExternalLinks(True)
            self.add_decoration_label("E-mail")
            link="pylablib@gmail.com"
            self.add_decoration_label("<a href='mailto: {link:}'>{link:}</a>".format(link=link),location=(-1,1)).setOpenExternalLinks(True)
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)