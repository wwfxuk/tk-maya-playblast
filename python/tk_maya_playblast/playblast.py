import datetime
import os
import pprint
import re
import shutil
import subprocess
import sys
import traceback

from contextlib import contextmanager

import tank
from tank.platform.qt import QtCore, QtGui
from .playblast_dialog import PlayblastDialog

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

class PlayblastManager(object):
    __uploadToShotgun = True
    __createVersion = False
    __showViewer = True

    """
    Main playblast functionality
    """
    def __init__(self, app, context=None):
        """
        Construction
        """
        self._app = app
        self._context = context if context else self._app.context

    def showDialog(self):
        try:
            self._app.engine.show_dialog("Playblast %s" % self._app.version,
                                         self._app, PlayblastDialog, self._app, self)
        except:
            traceback.print_exc()

    def doPlayblast(self, **overridePlayblastParams):
        template_work = self._app.get_template("template_work")
        template_shot = self._app.get_template("template_shot")
        sceneName = pm.sceneName()
        fields = template_work.get_fields(sceneName)
        self.shotPlayblastPath = template_shot.apply_fields(fields)

        # Get value of optional config field "temp_directory". If path is
        # invalid or not absolute, use default tempdir.
        temp_directory = os.path.normpath( self._app.get_setting("temp_directory", "default") )
        if not os.path.isabs(temp_directory):
            import tempfile
            temp_directory = tempfile.gettempdir()

        # make sure it is exists
        if not os.path.isdir(temp_directory):
            os.mkdir(temp_directory)
        # use the basename of generated names
        self.localPlayblastPath = os.path.join(temp_directory, os.path.basename(self.shotPlayblastPath))
        # run actual playblast routine
        self.__createPlayblast(**overridePlayblastParams)
        self._app.log_info("Playblast for %s succesful" % sceneName)
        
    def __createPlayblast(self, **overridePlayblastParams):
        localPlayblastPath = self.localPlayblastPath
        
        # setting playback range
        originalPlaybackRange = ( pm.playbackOptions( query=True, minTime=True ), 
                                  pm.playbackOptions( query=True, maxTime=True ))
        startTime = pm.playbackOptions( query=True, animationStartTime=True )
        endTime = pm.playbackOptions( query=True, animationEndTime=True )
        pm.playbackOptions( edit=True, minTime=startTime, maxTime=endTime )
        
        # get playblast parameters from hook
        playblastParams = self._app.execute_hook("hook_setup_window", action="playblast_params", data=localPlayblastPath)
        # get window and editor parameters from hook
        createWindow = self._app.execute_hook("hook_setup_window", action='create_window')

        # with the created window, do a playblast
        with createWindow():
            playblastParams.update(overridePlayblastParams)
            playblastSuccessful = False
            while not playblastSuccessful:
                try:
                    # set required visibleHUDs from hook
                    visibleHUDs = self._app.execute_hook("hook_setup_window", action="hud_set")

                    resultPlayblastPath = pm.playblast( **playblastParams )
                    playblastSuccessful = True
                except RuntimeError, e:
                    if os.path.exists(localPlayblastPath):
                        playblastSuccessful = True
                    else:
                        result = QtGui.QMessageBox.critical(None, u"Playblast Error",
                                                            unicode(e),
                                                            QtGui.QMessageBox.Retry | QtGui.QMessageBox.Abort)
                        if result == QtGui.QMessageBox.Abort:
                            self._app.logger.exception("Playblast aborted")
                            return
                finally:
                    # restore HUD state
                    self._app.execute_hook("hook_setup_window", action="hud_unset", data=visibleHUDs)
                    # restore playback range
                    originalMinTime, originalMaxTime = originalPlaybackRange
                    pm.playbackOptions( edit=True, minTime=originalMinTime, maxTime=originalMaxTime )

        # do post playblast process, copy files and other necessary stuff
        result = self._app.execute_hook("hook_post_playblast", action="copy_file", data=localPlayblastPath)
        
        if result:
            self._app.logger.info("Playblast local file created: %s", result)

        if self.__showViewer:
            self._app.logger.info("Opening RV...")
            subprocess.call(["rez", "env" , "rv", "--", "rv", str(localPlayblastPath)])

        if self.__createVersion:
            # register new Version entity in shotgun or update existing version, minimize shotgun data
            playblast_movie = self.shotPlayblastPath
            project = self._app.context.project
            entity = self._app.context.entity
            task = self._app.context.task

            data = { 'project': project,
                    'code': os.path.basename(playblast_movie),
                    'description': 'automatic generated by playblast app',
                    'sg_path_to_movie': playblast_movie,
                    'entity': entity,
                    'sg_task': task,
                }
            self._app.log_debug("Version-creation hook data:\n" + pprint.pformat(data))
            result = self._app.execute_hook("hook_post_playblast", action="create_version", data=data)
            self._app.log_debug("Version-creation hook result:\n" + pprint.pformat(result))

            # upload QT file if creation or update process run succesfully
            if result and self.__uploadToShotgun:
                result = self._app.execute_hook("hook_post_playblast", action="upload_movie",
                                                data={
                                                    "path": data["sg_path_to_movie"],
                                                    "project": project,
                                                    "version_id": result["id"],
                                                })

        self._app.log_info("Playblast finished")

    def setUploadToShotgun(self, value):
        self._app.log_debug("Upload to Shotgun set to %s" % value)
        self.__uploadToShotgun = value

    def setCreateVersion(self, value):
        self._app.log_debug("Create version set to %s" % value)
        self.__createVersion = value

    def setShowViewer(self, value):
        self._app.log_debug("Show viewer set to %s" % value)
        self.__showViewer = value

    
