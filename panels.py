import bpy

from .core import opencode_installer as installer
from .core import opencode_server as server
from .core import utils

MAX_MESSAGES_SHOWN = 12
MAX_LINES_PER_MESSAGE = 10

ROLE_ICONS = {
    "user": "USER",
    "assistant": "BLENDER",
}

ROLE_LABELS = {
    "user": "You",
    "assistant": "AI",
}


class VIEW3D_PT_ai_copilot_chat(bpy.types.Panel):
    bl_label = "AI Copilot"
    bl_idname = "VIEW3D_PT_ai_copilot_chat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI Copilot"

    def draw(self, context):
        layout = self.layout
        ai = context.scene.ai

        self._draw_status(layout, context)

        row = layout.row()
        row.scale_y = 1.2
        row.prop(ai, "input", text="")
        row.enabled = not ai.busy and (server.running() or server.is_up(ai.oc_port))

        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("ai_copilot.send", icon="PLAY")
        row.operator("ai_copilot.clear", text="", icon="TRASH")

        self._draw_image_row(layout, ai)

        if ai.busy:
            layout.label(text="Agent is working...", icon="TIME")
            return

        self._draw_history(layout, ai)

    def _draw_status(self, layout, context):
        ai = context.scene.ai
        box = layout.box()

        if installer.installing():
            box.label(text=ai.oc_status or "installing...", icon="TIME")
            box.progress(factor=ai.oc_progress, type="BAR")
            return

        if not installer.is_installed():
            box.label(text="Portable runtime not installed", icon="INFO")
            row = box.row()
            row.scale_y = 1.2
            row.operator("ai_copilot.install", icon="IMPORT")
            return

        if server.running() or server.is_up(ai.oc_port):
            box.label(text="OpenCode ready", icon="CHECKMARK")
            box.operator("ai_copilot.server_stop", text="Stop Server", icon="PAUSE")
        else:
            status = ai.oc_status or "server stopped"
            icon = "TIME" if "starting" in status else "ERROR" if "error" in status else "STATUS"
            box.label(text=status, icon=icon)
            row = box.row()
            row.scale_y = 1.2
            row.operator("ai_copilot.server_start", text="Start Server", icon="PLAY")

    def _draw_image_row(self, layout, ai):
        if ai.image_path:
            box = layout.box()
            row = box.row(align=True)
            name = ai.image_path.replace("\\", "/").split("/")[-1]
            row.label(text="Image: %s" % name, icon="FILE_IMAGE")
            row.operator("ai_copilot.clear_image", text="", icon="X")
        else:
            row = layout.row(align=True)
            row.operator("ai_copilot.attach_image", text="Image", icon="FILE_IMAGE")
            row.operator("ai_copilot.screenshot", text="Viewport", icon="CAMERA_DATA")

    def _draw_history(self, layout, ai):
        messages = list(ai.messages)
        if not messages:
            box = layout.box()
            box.alignment = 'CENTER'
            box.label(text="Describe what to build,", icon="BLENDER")
            box.label(text="attach an image, and press Send.")
            return
        if len(messages) > MAX_MESSAGES_SHOWN:
            layout.label(
                text="... %d earlier messages hidden" % (len(messages) - MAX_MESSAGES_SHOWN),
                icon="DOT",
            )
        for msg in messages[-MAX_MESSAGES_SHOWN:]:
            self._draw_message(layout, msg)

    def _draw_message(self, layout, msg):
        icon = ROLE_ICONS.get(msg.role, "QUESTION")
        is_error = msg.content.startswith("Error:")
        is_run = msg.content.startswith("[run]")
        if is_error:
            icon = "ERROR"
        elif is_run:
            icon = "CONSOLE"

        box = layout.box()
        box.label(text=ROLE_LABELS.get(msg.role, msg.role.capitalize()), icon=icon)
        body = box.column(align=True)
        body.scale_y = 0.9
        lines = utils.wrap_text(msg.content)
        shown = lines if len(lines) <= MAX_LINES_PER_MESSAGE else lines[:MAX_LINES_PER_MESSAGE]
        for line in shown:
            body.label(text=line)
        if len(lines) > MAX_LINES_PER_MESSAGE:
            body.label(text="... (%d more lines)" % (len(lines) - MAX_LINES_PER_MESSAGE))
        if msg.image:
            name = msg.image.replace("\\", "/").split("/")[-1]
            box.label(text="attachment: %s" % name, icon="FILE_IMAGE")


class VIEW3D_PT_ai_copilot_settings(bpy.types.Panel):
    bl_label = "AI Settings"
    bl_idname = "VIEW3D_PT_ai_copilot_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI Copilot"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        ai = context.scene.ai

        layout.prop(ai, "oc_provider")
        if ai.oc_provider != "ollama":
            layout.prop(ai, "oc_api_key")
        layout.prop(ai, "oc_model")
        layout.prop(ai, "oc_port")
        layout.prop(ai, "auto_run")
        layout.prop(ai, "oc_auto_fix")

        box = layout.box()
        box.scale_y = 0.85
        box.label(text="Model ID examples:", icon="URL")
        box.label(text="openai: gpt-4o")
        box.label(text="anthropic: claude-sonnet-4")
        box.label(text="ollama: llava (vision for images)")
        box.label(text="Logs: ai_copilot/server.log")


classes = (
    VIEW3D_PT_ai_copilot_chat,
    VIEW3D_PT_ai_copilot_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
