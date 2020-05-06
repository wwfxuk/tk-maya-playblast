# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import shutil
import traceback

import maya.cmds as cmds
import pymel.core as pm
import pprint

import sgtk

from datetime import datetime
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

class PostPlayblast(sgtk.Hook):
    """
    Hook called when a file needs to be copied
    """

    def copy_file(self, source=""):
        app = self.parent
        try:
            # get all required template
            template_work = app.get_template("template_work")
            templates = [
                app.get_template("template_shot"),
                app.get_template("template_sequence")
            ]
            # use current scene name to create valid QT file names
            scenename = pm.sceneName()
            fields = template_work.get_fields(scenename)
            # make sure that destination folder is exists
            for template in templates:
                if not template:
                    continue
                destination = template.apply_fields(fields)
                dirname = os.path.dirname(destination)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                shutil.copy(source, destination)
        except:
            app.logger.error("Error in copying file %s", source)
        return True

    def create_version(self, data={}):
        """
            Setting up shotgun version entity without uploading the QT file
        """
        app = self.parent
        sg = app.sgtk.shotgun
        current_datetime = datetime.now().strftime(TIMESTAMP_FORMAT)
        description_form = "{comment}s\n\nPublish by {username}s at {hostname}s on {datetime}s"
        data["description"] = description_form.format(
            comment=data["description"],
            datetime=current_datetime,
            username=os.environ.get("USERNAME", "unknown"),
            hostname=os.environ.get("COMPUTERNAME", "unknown")
       )
        app.logger.debug("Setting up shotgun version entity...")
        result = None
        try:
            # check if a version entity with same code exists in shotgun
            # if none, create a new version Entity with qtfile name as its code
            version = sg.find_one("Version", [["code", "is", data["code"]]])
            if version:
                app.logger.debug("Version already exist, updating")
                result = sg.update("Version", version["id"], data)
            else:
                app.logger.debug("Create a new Version as %s" % data["code"])
                result = sg.create("Version", data)
        except sgtk.TankError:
            app.logger.error("Unable to create a new version on shotgun", exc_info=True)
        finally:
            return result

    def upload_movie(self, data={}):
        """
            Sending it to shotgun
        """
        app = self.parent
        sg = app.sgtk.shotgun
        app.logger.debug("Send qtfile to Shotgun")
        try:
            movie_path = data["path"]
            result = None
            if os.path.exists(movie_path):
                app.logger.debug("Uploading movie to Shotgun: %s" % movie_path)
                result = sg.upload("Version", data["version_id"], movie_path, field_name="sg_uploaded_movie")
            return result
        except sgtk.TankError:
            app.logger.error("Unable to upload %s to Shotgun", movie_path, exc_info=True)
