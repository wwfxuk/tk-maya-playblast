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
import re

import maya.cmds as cmds
import pymel.core as pm
import traceback
from contextlib import contextmanager

import sgtk
from sgtk.platform.qt import QtGui

PLAYBLAST_WINDOW = "Playblast Window"

MODEL_EDITOR_PARAMS = {
    "activeView": True,
    "cameras": False,
    "controlVertices": False,
    "deformers": False,
    "dimensions": False,
    "displayAppearance": "smoothShaded",
    "displayLights": "default",
    "displayTextures": True,
    "dynamicConstraints": False,
    "fogging": False,
    "follicles": False,
    "grid": False,
    "handles": False,
    "headsUpDisplay": True,
    "hulls": False,
    "ignorePanZoom": False,
    "ikHandles": False,
    "imagePlane": True,
    "joints": False,
    "lights": False,
    "locators": False,
    "manipulators": False,
    "nurbsCurves": False,
    "nurbsSurfaces": False,
    "pivots": False,
    "planes": False,
    "selectionHiliteDisplay": False,
    "shadows": False,
    "sortTransparent": True,
    "strokes": True,
    "textures": True,
    "useDefaultMaterial": False,
    "wireframeOnShaded": False,
    }

PLAYBLAST_PARAMS = {
    "forceOverwrite": True,
    "format": "qt",
    "framePadding": 4,
    "compression": "H.264",
    "offScreen": True,
    "percent": 100,
    "showOrnaments": True,
    "viewer": False,
    "sequenceTime": 0,
    "clearCache": True,
    "quality": 70,
    }

class SetupWindow(sgtk.Hook):
    """
    Hook called when creating playblast
    """

    def set_hud(self):
        visible_huds = [f for f in pm.headsUpDisplay(listHeadsUpDisplays=True)
                                if pm.headsUpDisplay(f, query=True, visible=True)]
        # hide all visible HUDs
        map(lambda f: pm.headsUpDisplay(f, edit=True, visible=False), visible_huds)

        # Add required HUD
        # User name
        edit_existing_hud = "HUDUserName" in pm.headsUpDisplay(listHeadsUpDisplays=True)
        pm.headsUpDisplay("HUDUserName", edit=edit_existing_hud,
                            command=lambda: os.getenv("USERNAME", "unknown.user"),
                            event="playblasting", section=1, block=1)
        pm.headsUpDisplay("HUDUserName", edit=True, visible=True, label="User:")
        # Scene name
        edit_existing_hud = "HUDSceneName" in pm.headsUpDisplay(listHeadsUpDisplays=True)
        pm.headsUpDisplay("HUDSceneName", edit=edit_existing_hud,
                            command=lambda: cmds.file(query=True, location=True, shortName=True).rsplit(".", 1)[0],
                            event="playblasting", section=6, block=1)
        pm.headsUpDisplay("HUDSceneName", edit=True, visible=True, label="Shot:")
        # Focal length
        pm.headsUpDisplay("HUDFocalLength", edit=True, visible=True, section=3, block=1)
        pm.headsUpDisplay("HUDCurrentFrame", edit=True, visible=True, dataFontSize="large", section=8, block=1)

        return visible_huds

    def unset_huds(self, huds=[]):
        # restore HUD state
        map(lambda f: pm.headsUpDisplay(f, edit=True, visible=False), pm.headsUpDisplay(listHeadsUpDisplays=True))
        map(lambda f: pm.headsUpDisplay(f, edit=True, visible=True), huds)

    def get_playblast_params(self, filename=""):
        app = self.parent
        playblast_params = dict(app.playblast_parameters)
        playblast_params["filename"] = filename
        # include audio if available
        audio_list = pm.ls(type="audio")
        if audio_list:
            playblast_params["sound"] = audio_list[0]
        return playblast_params

    @contextmanager
    def create_window(self, template_name=""):
        # setting up context window for playblast

        """ try to get data from shotgun project fields
            need to get context's project
                        context's shotgun instance
        """
        app = self.parent
        model_editor_params = app.model_editor_templates.get(template_name, {})

        video_width = cmds.getAttr("defaultResolution.width")
        video_height = cmds.getAttr("defaultResolution.height")

        panel_name = cmds.getPanel(withFocus=True)
        if panel_name not in cmds.getPanel(type="modelPanel"):
            message = "Please select a viewport before trying to render"
            self.logger.error(message)
            QtGui.QMessageBox.critical(None, "No Viewport selected", message)
            raise RuntimeError(message)

        camera_trans = cmds.modelEditor(panel_name, q=True, cam=True)
        camera = cmds.ls(camera_trans, dag=True, cameras=True)[0]
        model_editor_params["cam"] = camera

        # Give Viewport 2.0 renderer only for Maya 2015++
        mayaVersionString = cmds.about(version=True)
        mayaVersion = int(mayaVersionString[:4]) if len(mayaVersionString) >= 4 else 0
        if mayaVersion >= 2015:
            model_editor_params["rendererName"] = "vp2Renderer"

        # Create window
        if pm.windowPref(PLAYBLAST_WINDOW, exists=True):
            pm.windowPref(PLAYBLAST_WINDOW, remove=True)
        window = pm.window(
            PLAYBLAST_WINDOW,
            titleBar=True,
            iconify=True,
            leftEdge=100,
            topEdge=100,
            width=video_width,
            height=video_height,
            sizeable=False
        )
        # Create editor area
        layout = pm.formLayout()
        editor = pm.modelEditor(**model_editor_params)
        pm.setFocus(editor)
        pm.formLayout(
            layout,
            edit=True,
            attachForm=(
                (editor, "left", 0),
                (editor, "top", 0),
                (editor, "right", 0),
                (editor, "bottom", 0)
            )
        )
        # Show window
        pm.setFocus(editor)
        pm.showWindow(window)
        import pprint
        pm.refresh()
        app.logger.debug(pprint.pformat(model_editor_params))
        try:
            yield editor
        except:
            traceback.print_exc()
        finally:
            pm.deleteUI(window)

