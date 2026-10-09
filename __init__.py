bl_info = {
    "name": "AI Copilot",
    "author": "AI Copilot Contributors",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > Sidebar (N) > AI Copilot",
    "description": "Chat with an OpenCode-powered AI agent inside Blender: send text or images, get working bpy code executed in your scene.",
    "doc_url": "https://github.com/BlenderGPT3D/blender-ai-addon",
    "category": "3D View",
}

import bpy
from bpy.props import PointerProperty

from . import properties, operators, panels

classes = (
    properties.AIMessage,
    properties.AIProperties,
    operators.AICopilotInstall,
    operators.AICopilotServerStart,
    operators.AICopilotServerStop,
    operators.AICopilotAttachImage,
    operators.AICopilotScreenshot,
    operators.AICopilotClearImage,
    operators.AICopilotSend,
    operators.AICopilotRunLast,
    operators.AICopilotClear,
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
