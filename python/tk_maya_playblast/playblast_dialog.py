
import sgtk
import os
import sys
import threading

from sgtk.platform.qt import QtCore, QtGui

SCALE_OPTIONS = [50, 100]

class PlayblastDialog(QtGui.QWidget):
    """
    Main application dialog window
    """

    def __init__(self, app, handler, parent=None):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        super(PlayblastDialog, self).__init__(parent)

        self._app = app
        self._handler = handler

        self._build_ui()

        self._init_components()

        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        # self._app = sgtk.platform.current_bundle()

        # via the self._app handle we can for example access:
        # - The engine, via self._app.engine
        # - A Shotgun API instance, via self._app.shotgun
        # - A tk API instance, via self._app.tk

        # lastly, set up our very basic UI
        # self.context.setText("Current Shot: %s" % self._app.context)
        self.btn_playblast.clicked.connect(self.do_playblast)

    def _build_ui(self):
        settings = sgtk.platform.import_framework("tk-framework-shotgunutils", "settings")
        self._settings = settings.UserSettings(self._app)
        self.resize(468, 67)
        layout = QtGui.QGridLayout(self)
        self.cmb_percentage = QtGui.QComboBox(self)
        layout.addWidget(self.cmb_percentage, 0, 0)
        self.chb_create_version = QtGui.QCheckBox("Create New Version", self)
        version_checked = self._settings.retrieve("create_version", default=False)
        self.chb_create_version.setChecked(version_checked)
        layout.addWidget(self.chb_create_version, 0, 1)
        self.chb_upload_to_shotgun = QtGui.QCheckBox("Upload to Shotgun", self)
        upload_checked = self._settings.retrieve("upload_version", default=True)
        self.chb_upload_to_shotgun.setChecked(upload_checked)
        self.chb_upload_to_shotgun.setEnabled(version_checked)
        self.chb_create_version.toggled.connect(self.chb_upload_to_shotgun.setEnabled)
        layout.addWidget(self.chb_upload_to_shotgun, 0, 2)
        self.chb_show_viewer = QtGui.QCheckBox("Show Viewer", self)
        viewer_checked = self._settings.retrieve("show_viewer", default=True)
        self.chb_show_viewer.setChecked(viewer_checked)
        layout.addWidget(self.chb_show_viewer, 0, 3)
        self.btn_playblast = QtGui.QPushButton("Playblast", self)
        self.btn_playblast.setMinimumSize(450, 0)
        layout.addWidget(self.btn_playblast, 1, 0, 1, 4)

    def _init_components(self):
        # Setting up playblast resolution percentage. Customizable through
        # optional "scale_options" field in app settings.
        scale_int_list = self._app.get_setting("scale_options")
        for percent_int in sorted(scale_int_list, reverse=True):
            self.cmb_percentage.addItem("%d%%" % percent_int, userData=percent_int)
        setting_percent = self._settings.retrieve("percent_scale", default=100)
        index = self.cmb_percentage.findData(setting_percent)
        index = index if index > 0 else 0
        self.cmb_percentage.setCurrentIndex(index)

    def do_playblast(self):
        override_playblast_params = {}

        create_version = self.chb_create_version.isChecked()
        self._handler.set_create_version(create_version)

        upload_to_shotgun = self.chb_upload_to_shotgun.isChecked()
        self._handler.set_upload_to_shotgun(upload_to_shotgun)

        show_viewer = self.chb_show_viewer.isChecked()
        self._handler.set_shot_viewer(show_viewer)

        percent_int = self.cmb_percentage.itemData(self.cmb_percentage.currentIndex())
        override_playblast_params["percent"] = percent_int
        self._handler.do_playblast(**override_playblast_params)

    def closeEvent(self, event):
        create_version = self.chb_create_version.isChecked()
        self._settings.store("create_version", create_version)
        upload_to_shotgun = self.chb_upload_to_shotgun.isChecked()
        self._settings.store("upload_version", upload_to_shotgun)
        show_viewer = self.chb_show_viewer.isChecked()
        self._settings.store("show_viewer", show_viewer)
        percent_int = self.cmb_percentage.itemData(self.cmb_percentage.currentIndex())
        self._settings.store("percent_scale", percent_int)
        super(PlayblastDialog, self).closeEvent(event)
