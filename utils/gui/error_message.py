from pylablib.core.gui import QtCore, QtWidgets

class ErrorBox(QtWidgets.QFrame):
    """Window with the error info"""
    def setup(self, error_msg):
        self.setWindowTitle("Error")
        self.setWindowFlag(QtCore.Qt.Dialog)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint,False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint,False)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setMaximumWidth(500)
        self.main_layout=QtWidgets.QHBoxLayout(self)
        icon=self.style().standardIcon(self.style().SP_MessageBoxCritical)
        self.icon_label=QtWidgets.QLabel(parent=self)
        self.icon_label.setPixmap(icon.pixmap(64,64))
        self.main_layout.addWidget(self.icon_label,0,QtCore.Qt.AlignTop)
        self.text_layout=QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.text_layout)
        self.header_label=QtWidgets.QLabel(text="An error occurred",parent=self)
        self.text_layout.addWidget(self.header_label)
        self.message_label=QtWidgets.QLabel(text="  "+error_msg,parent=self)
        self.message_label.setWordWrap(True)
        self.text_layout.addWidget(self.message_label)
        link="https://github.com/SandoghdarLab/pyLabLib-cam-control/issues"
        email="pylablib@gmail.com"
        contact_text="If the error keeps occuring, contact the developer on <a href='{link:}'>GitHub</a> or via email at <a href='{email:}'>{email:}</a>".format(link=link,email=email)
        self.contact_label=QtWidgets.QLabel(text=contact_text,parent=self)
        self.contact_label.setOpenExternalLinks(True)
        self.text_layout.addWidget(self.contact_label)
        self.exit_button=QtWidgets.QPushButton(text="OK",parent=self)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setFixedWidth(self.exit_button.width())
        self.text_layout.addWidget(self.exit_button,0,QtCore.Qt.AlignRight)
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)