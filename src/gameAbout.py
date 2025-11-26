from PyQt5 import QtGui
from ui.ui_about import Ui_Form
from ui.uiComponents import RoundQDialog

class ui_Form(Ui_Form):
    def __init__(self, r_path, parent):
        # 关于界面，继承一下就好
        self.Dialog = RoundQDialog(parent)
        self.setupUi (self.Dialog)
        self.Dialog.setWindowIcon (QtGui.QIcon (str(r_path.with_name('media').joinpath('cat.ico'))))
        self.pushButton.setStyleSheet("border-image: url(" + str(r_path.with_name('media').joinpath('button.png')).replace("\\", "/") + ");\n"
"font: 16pt \"黑体\";\n"
"color:white;font: bold;")
        self.label_6.setStyleSheet("border-image: url(" + str(r_path.with_name('media').joinpath('github.svg')).replace("\\", "/") + ");")
        self.label_7.setStyleSheet("border-image: url(" + str(r_path.with_name('media').joinpath('message.svg')).replace("\\", "/") + ");")
        
        


