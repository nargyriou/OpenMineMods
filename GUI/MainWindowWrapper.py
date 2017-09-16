from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread

from functools import partial
from os import path
from sys import platform
from webbrowser import open as webopen

from API.CurseAPI import CurseAPI
from API.MultiMC import MultiMC, MultiMCInstance

from Utils.Utils import clear_layout, confirm_box, dir_box
from Utils.Analytics import send_data
from Utils.Updater import UpdateCheckThread

from GUI.MainWindow import Ui_MainWindow

from GUI.InstanceWindowWrapper import InstanceWindow

from GUI.AnalyticsDialog import Ui_AnalyticsDialog
from GUI.UpdateDialog import Ui_UpdateDialog

from GUI.InstanceWidget import Ui_InstanceWidget
from GUI.PackWidget import Ui_PackWidget


class MainWindow:
    def __init__(self):
        self.curse = CurseAPI()
        self.win = QMainWindow()

        self.win.setWindowTitle("OpenMineMods v{}".format(self.curse.version))

        while not self.curse.baseDir:
            self.curse.baseDir = dir_box(self.win, "Select Your MultiMC Folder", path.expanduser("~"))
            self.curse.db["baseDir"] = self.curse.baseDir

        if "updater" not in self.curse.db:
            self.curse.db["updater"] = True

        if "analytics" not in self.curse.db:
            ad = QDialog(self.win)
            ad.setWindowTitle("OpenMineMods Setup")
            an = Ui_AnalyticsDialog()
            an.setupUi(ad)
            self.curse.db["analytics"] = ad.exec_()
            if self.curse.db["analytics"]:
                send_data(self.curse)

        self.mmc = MultiMC(self.curse.baseDir)

        self.children = list()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.win)

        self.init_instances()
        self.init_packs()

        self.ui.mmc_folder.setText(self.curse.baseDir)

        self.ui.analytics_check.setChecked(self.curse.db["analytics"])
        self.ui.analytics_check.clicked.connect(self.analytics_checked)

        self.ui.update_check.setChecked(self.curse.db["updater"])
        self.ui.update_check.clicked.connect(self.update_checked)

        self.win.show()

        if self.curse.db["updater"]:
            self.update_tr = QThread()
            self.uc = UpdateCheckThread(self.curse)
            self.uc.done.connect(self.update_check_done)

            self.uc.moveToThread(self.update_tr)
            self.update_tr.started.connect(self.uc.check_updates)

            self.update_tr.start()


    """UI Initializations"""

    def init_instances(self):
        clear_layout(self.ui.instance_box)

        for instance in self.mmc.instances:
            widget = QWidget()
            el = Ui_InstanceWidget()

            el.setupUi(widget)

            el.instance_delete.clicked.connect(partial(self.delete_clicked, instance))
            el.instance_edit.clicked.connect(partial(self.edit_clicked, instance))

            el.instance_name.setText(instance.name)

            self.ui.instance_box.addWidget(widget)

        self.ui.instance_box.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def init_packs(self):
        clear_layout(self.ui.pack_box)

        for pack in ["Test", "Test1"] * 20:
            widget = QWidget()
            el = Ui_PackWidget()

            el.setupUi(widget)

            el.pack_name.setText(pack)

            self.ui.pack_box.addWidget(widget)

        self.ui.pack_box.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    """Event Listeners"""

    def delete_clicked(self, instance: MultiMCInstance):
        print(confirm_box(self.win, QMessageBox.Question,
                          "Are you sure you want to delete {}".format(instance.name)))

    def edit_clicked(self, instance: MultiMCInstance):
        self.children.append(InstanceWindow(instance))

    def analytics_checked(self):
        self.curse.db["analytics"] = self.ui.analytics_check.isChecked()

    def update_checked(self):
        self.curse.db["updater"] = self.ui.update_check.isChecked()

    def update_check_done(self, res: dict):
        if not res["res"] or not res["update"]["downloads"][platform]:
            return

        up_win = QDialog()
        upd = Ui_UpdateDialog()
        upd.setupUi(up_win)

        upd.textBrowser.setText(res["update"]["changelog"])

        if not up_win.exec_():
            return