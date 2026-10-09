bl_info = {
    "name": "AI Copilot",
    "author": "AI Copilot Contributors",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > Sidebar (N) > AI Copilot",
    "description": "Create and edit 3D models by chatting with an AI. Send images and get bpy code that runs in your scene.",
    "doc_url": "https://github.com/BlenderGPT3D/blender-ai-addon",
    "category": "3D View",
}

import bpy
from bpy.props import PointerProperty

from . import properties, operators, panels

classes = (
    properties.AIMessage,
    properties.AIProperties,
    operators.AICopilotSend,
    operators.AICopilotClear,
    operators.AICopilotRunLast,
    operators.AICopilotAttachImage,
    operators.AICopilotScreenshot,
    operators.AICopilotClearImage,
    panels.VIEW3D_PT_ai_copilot_chat,
    panels.VIEW3D_PT_ai_copilot_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ai = PointerProperty(type=properties.AIProperties)


def unregister():
    del bpy.types.Scene.ai
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
