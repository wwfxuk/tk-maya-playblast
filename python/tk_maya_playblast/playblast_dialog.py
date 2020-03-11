
import tank
import os
import sys
import threading

from tank.platform.qt import QtCore, QtGui

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
        
        self.__initComponents()
        
        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        # self._app = tank.platform.current_bundle()
        
        # via the self._app handle we can for example access:
        # - The engine, via self._app.engine
        # - A Shotgun API instance, via self._app.shotgun
        # - A tk API instance, via self._app.tk 
        
        # lastly, set up our very basic UI
        # self.context.setText("Current Shot: %s" % self._app.context)
        self.btnPlayblast.clicked.connect(self.doPlayblast)

    def _build_ui(self):
        self.resize(468, 67)
        layout = QtGui.QGridLayout(self)
        self.cmbPercentage = QtGui.QComboBox(self)
        layout.addWidget(self.cmbPercentage, 0, 0)
        self.chbCreateVersion = QtGui.QCheckBox("Create New Version", self)
        self.chbCreateVersion.setChecked(False)
        layout.addWidget(self.chbCreateVersion, 0, 1)
        self.chbUploadToShotgun = QtGui.QCheckBox("Upload to Shotgun", self)
        self.chbUploadToShotgun.setChecked(True)
        self.chbUploadToShotgun.setEnabled(False)
        self.chbCreateVersion.toggled.connect(self.chbUploadToShotgun.setEnabled)
        layout.addWidget(self.chbUploadToShotgun, 0, 2)
        self.chbShowViewer = QtGui.QCheckBox("Show Viewer", self)
        self.chbShowViewer.setChecked(True)
        layout.addWidget(self.chbShowViewer, 0, 3)
        self.btnPlayblast = QtGui.QPushButton("Playblast", self)
        self.btnPlayblast.setMinimumSize(450, 0)
        layout.addWidget(self.btnPlayblast, 1, 0, 1, 4)

    def __initComponents(self):
        # Setting up playblast resolution percentage. Customizable through
        # optional "scale_options" field in app settings.
        scaleIntList = self._app.get_setting("scale_options", SCALE_OPTIONS)
        for percentInt in scaleIntList:
            self.cmbPercentage.addItem( "%d%%" % percentInt, userData=percentInt )

    def doPlayblast(self):
        overridePlayblastParams = {}

        createVersion = self.chbCreateVersion.isChecked()
        self._handler.setCreateVersion( createVersion )

        uploadToShotgun = self.chbUploadToShotgun.isChecked()
        self._handler.setUploadToShotgun( uploadToShotgun )

        showViewer = self.chbShowViewer.isChecked()
        self._handler.setShowViewer( showViewer )
        overridePlayblastParams["viewer"] = showViewer

        percentInt = self.cmbPercentage.itemData( self.cmbPercentage.currentIndex() )
        overridePlayblastParams["percent"] = percentInt
        self._handler.doPlayblast(**overridePlayblastParams)

