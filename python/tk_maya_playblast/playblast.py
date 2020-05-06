import os
import pprint
import subprocess

from sgtk.platform.qt import QtCore, QtGui
from .playblast_dialog import PlayblastDialog

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

class PlayblastManager(object):
    __upload_to_shotgun = True
    __create_version = False
    __show_viewer = True

    """
    Main playblast functionality
    """
    def __init__(self, app, context=None):
        """
        Construction
        """
        self._app = app
        self._context = context if context else self._app.context

    def show_dialog(self):
        try:
            self._app.engine.show_dialog(
                "Playblast %s" % self._app.version,
                self._app,
                PlayblastDialog,
                self._app,
                self
            )
        except Exception:
            self._app.logger.error("Unable to show dialog.", exc_info=True)

    def do_playblast(self, **override_playblast_params):
        template_work = self._app.get_template("template_work")
        template_shot = self._app.get_template("template_shot")
        scene_name = pm.sceneName()
        fields = template_work.get_fields(scene_name)
        shot_playblast_path = template_shot.apply_fields(fields)

        # Get value of optional config field "temp_directory". If path is
        # invalid or not absolute, use default tempdir.
        temp_directory = os.path.normpath(self._app.get_setting("temp_directory", "default"))
        if not os.path.isabs(temp_directory):
            import tempfile
            temp_directory = tempfile.gettempdir()

        # make sure it is exists
        if not os.path.isdir(temp_directory):
            os.mkdir(temp_directory)
        # use the basename of generated names
        local_playblast_path = os.path.join(temp_directory, os.path.basename(shot_playblast_path))
        # run actual playblast routine
        self._create_playblast(shot_playblast_path, local_playblast_path, override_playblast_params)
        self._app.logger.info("Playblast for %s succesful" % scene_name)

    def _create_playblast(self, shot_playblast_path, local_playblast_path, override_playblast_params):

        # setting playback range
        original_playback_range = (
            pm.playbackOptions(query=True, minTime=True),
            pm.playbackOptions(query=True, maxTime=True)
        )
        start_time = pm.playbackOptions(query=True, animationStartTime=True)
        end_time = pm.playbackOptions(query=True, animationEndTime=True)
        pm.playbackOptions(edit=True, minTime=start_time, maxTime=end_time)

        # get playblast parameters from hook
        playblast_params = self._app.execute_hook_method(
            "hook_setup_window",
            "get_playblast_params",
            filename=local_playblast_path
        )
        # get window and editor parameters from hook
        with self._app.execute_hook_method("hook_setup_window", "create_window") as model_editor:
            playblast_params.update(override_playblast_params)
            playblast_params["editorPanelName"] = model_editor
            self._app.logger.debug(pprint.pformat(playblast_params))
            playblast_successful = False
            while not playblast_successful:
                visible_huds = []
                try:
                    # set required visible_huds from hook
                    visible_huds = self._app.execute_hook_method("hook_setup_window", "set_hud")

                    pm.playblast(**playblast_params)
                    playblast_successful = True
                except RuntimeError, e:
                    if os.path.exists(local_playblast_path):
                        playblast_successful = True
                    else:
                        result = QtGui.QMessageBox.critical(
                            None,
                            u"Playblast Error",
                            unicode(e),
                            QtGui.QMessageBox.Retry | QtGui.QMessageBox.Abort
                       )
                        if result == QtGui.QMessageBox.Abort:
                            self._app.logger.exception("Playblast aborted")
                            return
                finally:
                    # restore HUD state
                    self._app.execute_hook_method("hook_setup_window", "unset_huds", huds=visible_huds)
                    # restore playback range
                    original_min_time, original_max_time = original_playback_range
                    pm.playbackOptions(edit=True, minTime=original_min_time, maxTime=original_max_time)

        # do post playblast process, copy files and other necessary stuff
        result = self._app.execute_hook_method("hook_post_playblast", "copy_file", source=local_playblast_path)

        if result:
            self._app.logger.info("Playblast local file created: %s", result)

        if self.__show_viewer:
            self._app.logger.info("Opening RV...")
            subprocess.call(["rez", "env" , "rv", "--", "rv", str(local_playblast_path)])

        if self.__create_version:
            # register new Version entity in shotgun or update existing version, minimize shotgun data
            playblast_movie = shot_playblast_path
            project = self._app.context.project
            entity = self._app.context.entity
            task = self._app.context.task

            data = {
                "project": project,
                "code": os.path.basename(playblast_movie),
                "description": "automatic generated by playblast app",
                "sg_path_to_movie": playblast_movie,
                "entity": entity,
                "sg_task": task,
            }
            self._app.logger.debug("Version-creation hook data:\n%s", pprint.pformat(data))
            result = self._app.execute_hook_method("hook_post_playblast", "create_version", data=data)
            self._app.logger.debug("Version-creation hook result:\n%s", pprint.pformat(result))

            # upload QT file if creation or update process run succesfully
            if result and self.__upload_to_shotgun:
                result = self._app.execute_hook_method(
                    "hook_post_playblast",
                    "upload_movie",
                    data={
                        "path": data["sg_path_to_movie"],
                        "project": project,
                        "version_id": result["id"],
                    }
                )

        self._app.logger.info("Playblast finished")

    def set_upload_to_shotgun(self, value):
        self._app.logger.debug("Upload to Shotgun set to %s" % value)
        self.__upload_to_shotgun = value

    def set_create_version(self, value):
        self._app.logger.debug("Create version set to %s" % value)
        self.__create_version = value

    def set_shot_viewer(self, value):
        self._app.logger.debug("Show viewer set to %s" % value)
        self.__show_viewer = value
