# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
An app that syncs the frame range between a scene and a shot in Shotgun.

"""
from sgtk.platform import Application


class BasePlayblast(Application):
    playblast_manager = None

    def init_app(self):
        """
        Called as the application is being initialized
        """
        self.engine.register_command(self.get_setting("menu_name"), self.run_app)
        self._model_editor_parameters = self.get_setting("model_editor_parameters")
        self._playblast_parameters = self.get_setting("playblast_parameters")

    @property
    def playblast_parameters(self):
        return self._playblast_parameters

    @property
    def model_editor_parameters(self):
        return self._model_editor_parameters

    def destroy_app(self):
        """
        App teardown
        """
        self.log_debug("Destroying playblast app")

    def run_app(self):
        """
        Start doing playblast
        """
        try:
            playblast_manager = self.get_playblast_manager()
            playblast_manager.show_dialog()
        except Exception:
            self.logger.error("Unable to launch playblast manager", exc_info=True)

    def get_playblast_manager(self):
        """
        Create a singleton PlayblastManager object to be used by any app.
        """
        if self.playblast_manager is None:
            tk_maya_playblast = self.import_module("tk_maya_playblast")
            self.playblast_manager = tk_maya_playblast.PlayblastManager(self)
        return self.playblast_manager


