import os
import tempfile
import threading

import bpy

from .core import ai_client, executor, prompts, utils

_JOB = {}


class AICopilotAttachImage(bpy.types.Operator):
    bl_idname = "ai_copilot.attach_image"
    bl_label = "Attach Image"
    bl_description = "Attach a reference image to the next message"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        context.scene.ai.image_path = self.filepath
        return {'FINISHED'}


class AICopilotScreenshot(bpy.types.Operator):
    bl_idname = "ai_copilot.screenshot"
    bl_label = "Attach Viewport"
    bl_description = "Capture the current viewport as a reference image"
    bl_options = {'REGISTER'}

    def execute(self, context):
        path = os.path.join(tempfile.gettempdir(), "ai_copilot_reference.png")
        try:
            bpy.ops.screen.screenshot_area(filepath=path)
        except Exception:
            bpy.ops.screen.screenshot(filepath=path)
        context.scene.ai.image_path = path
        self.report({'INFO'}, "Viewport screenshot attached")
        return {'FINISHED'}


class AICopilotClearImage(bpy.types.Operator):
    bl_idname = "ai_copilot.clear_image"
    bl_label = "Remove Image"
    bl_description = "Remove the attached image"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        context.scene.ai.image_path = ""
        return {'FINISHED'}


class AICopilotSend(bpy.types.Operator):
    bl_idname = "ai_copilot.send"
    bl_label = "Send"
    bl_description = "Send the message (and attached image) to the AI"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ai = getattr(context.scene, "ai", None)
        return ai is not None and not ai.busy and bool(ai.input.strip())

    def execute(self, context):
        ai = context.scene.ai
        text = ai.input.strip()
        image = ai.image_path if os.path.isfile(ai.image_path) else ""
        utils.add_message(context, "user", text, image)
        ai.input = ""
        ai.image_path = ""

        system_prompt = prompts.build_system_prompt(context.scene)
        payload = ai_client.build_payload(ai.messages, system_prompt)

        ai.busy = True
        utils.redraw_all(context)

        result = {}

        def worker():
            try:
                result["reply"] = ai_client.send_chat(
                    ai.api_base,
                    ai.api_key,
                    ai.model,
                    payload,
                    temperature=ai.temperature,
                    max_tokens=ai.max_tokens,
                )
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        _JOB["thread"] = thread
        _JOB["result"] = result
        bpy.app.timers.register(_poll_job, first_interval=0.3)
        return {'FINISHED'}


def _poll_job():
    thread = _JOB.get("thread")
    if thread is not None and thread.is_alive():
        return 0.3

    result = _JOB.pop("result", {})
    _JOB.clear()

    context = bpy.context
    ai = context.scene.ai

    error = result.get("error")
    reply = result.get("reply")

    if error:
        utils.add_message(context, "assistant", "Error: %s" % error)
    elif reply:
        utils.add_message(context, "assistant", reply)
        if ai.auto_run:
            _run_blocks(context, utils.extract_code(reply))

    ai.busy = False
    utils.redraw_all(context)
    return None


def _run_blocks(context, blocks):
    for code in blocks:
        ok, stdout, err = executor.run_code(code)
        if ok:
            if stdout.strip():
                text = "Code executed. Output:\n%s" % utils.truncate(stdout.strip())
            else:
                text = "Code executed successfully."
        else:
            text = "Execution failed:\n%s\n%s" % (utils.truncate(stdout.strip()), utils.truncate(err.strip()))
        utils.add_message(context, "assistant", "[run] " + text)


class AICopilotRunLast(bpy.types.Operator):
    bl_idname = "ai_copilot.run_last"
    bl_label = "Run Last Code"
    bl_description = "Re-run the code from the last AI response"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ai = getattr(context.scene, "ai", None)
        if not ai:
            return False
        return any(utils.extract_code(m.content) for m in ai.messages if m.role == "assistant")

    def execute(self, context):
        for msg in reversed(list(context.scene.ai.messages)):
            if msg.role == "assistant":
                blocks = utils.extract_code(msg.content)
                if blocks:
                    _run_blocks(context, blocks)
                    utils.redraw_all(context)
                    return {'FINISHED'}
        return {'CANCELLED'}


class AICopilotClear(bpy.types.Operator):
    bl_idname = "ai_copilot.clear"
    bl_label = "Clear Chat"
    bl_description = "Clear the conversation history"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.ai.messages.clear()
        utils.redraw_all(context)
        return {'FINISHED'}


classes = (
    AICopilotAttachImage,
    AICopilotScreenshot,
    AICopilotClearImage,
    AICopilotSend,
    AICopilotRunLast,
    AICopilotClear,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
