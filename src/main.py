# from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5 import QtWidgets
import sys
import mainWindowGUI as mainWindowGUI
import mineSweeperGUI as mineSweeperGUI

if __name__ == "__main__":
    # appctxt = ApplicationContext()   # 1. Instantiate ApplicationContext
    app = QtWidgets.QApplication (sys.argv)
    # app.aboutToQuit.connect(app.deleteLater)
    mainWindow = mainWindowGUI.MainWindow ()
    ui = mineSweeperGUI.MineSweeperGUI (mainWindow)
    mainWindow.show()
    # exit_code = appctxt.app.exec_()  # 2. Invoke appctxt.app.exec_()
    sys.exit (app.exec_())



#bug:
#    自定义模式的鲁棒性
#    雷密度较大时，生成无猜局面采用自适应的鲁棒“快速模式”
#    生成极端bv局面时采用鲁棒的“快速模式”，仅对标准模式有效？
#    “高级设置”中增加可选择的无猜局面算法（筛选算法或修改算法）
#    快速给出多变量方程的一个解的算法
#    计算每格概率的子函数
#    “可能在标记双击未打开局面时，按下方格的阴影没有恢复”
#    加入AI模式
#    自动重开、自动弹成绩、获胜弹成绩等可选的功能
#    改级别时会闪
#    点脸后移开在别处弹起导致脸变大
#    自定义局面数值太大时崩溃
#    自定义模式bug较多




