from PyQt5 import QtGui
from ui.ui_about import Ui_Form
from ui.uiComponents import RoundQDialog
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt

class ui_Form(Ui_Form):
    def __init__(self, r_path, parent):
        self.Dialog = RoundQDialog(parent)
        self.setupUi(self.Dialog)

        # Fix up resource paths (same pattern as videoControl.py)
        m = r_path.with_name('media').as_posix()
        self.label_10.setStyleSheet(
            self.label_10.styleSheet().replace("url(media/", f"url({m}/"))
        self.label_12.setStyleSheet(
            self.label_12.styleSheet().replace("url(media/", f"url({m}/"))
        icon_path = str(r_path.with_name('media').joinpath('cat.ico'))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.Dialog.setWindowIcon(icon)

        # 空格键快捷键关闭这个窗口。回车不需要设置，在ui文件中已经设置。
        QShortcut(QKeySequence("Space"), self.Dialog, activated=self.pushButton.click)

