import bpy

from .core import utils

MAX_MESSAGES_SHOWN = 12
MAX_LINES_PER_MESSAGE = 10

ROLE_ICONS = {
    "user": "USER",
    "assistant": "BLENDER",
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

        row = layout.row()
        row.scale_y = 1.2
        row.prop(ai, "input", text="")
        row.enabled = not ai.busy

        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("ai_copilot.send", icon="PLAY")
        row.operator("ai_copilot.clear", text="", icon="TRASH")

        self._draw_image_row(layout, ai)

        if ai.busy:
            layout.label(text="Thinking...", icon="TIME")
            return

        self._draw_history(layout, ai)

    def _draw_image_row(self, layout, ai):
        if ai.image_path:
            box = layout.box()
            row = box.row(align=True)
            row.label(text="Image: %s" % (ai.image_path.replace("\\", "/").split("/")[-1]), icon="FILE_IMAGE")
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
            layout.label(text="... %d earlier messages hidden" % (len(messages) - MAX_MESSAGES_SHOWN), icon="DOT")
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
            box.label(text="attachment: %s" % msg.image.replace("\\", "/").split("/")[-1], icon="FILE_IMAGE")


ROLE_LABELS = {
    "user": "You",
    "assistant": "AI",
}


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

        layout.prop(ai, "api_base")
        layout.prop(ai, "api_key")
        layout.prop(ai, "model")
        layout.prop(ai, "temperature")
        layout.prop(ai, "max_tokens")
        layout.prop(ai, "auto_run")

        box = layout.box()
        box.scale_y = 0.85
        box.label(text="Works with any OpenAI-compatible API:", icon="URL")
        box.label(text="OpenAI, OpenRouter, Ollama,")
        box.label(text="LM Studio, DeepSeek, Groq...")
        row = box.row(align=True)
        row.label(text="Ollama base URL:")
        row2 = box.row(align=True)
        row2.label(text="http://localhost:11434/v1")


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
