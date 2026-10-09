import os
import tempfile
import threading

import bpy

from .core import executor, prompts, utils
from .core import opencode_installer as installer
from .core import opencode_server as server

_JOB = {}
_SERVER = {"thread": None, "error": ""}


class AICopilotInstall(bpy.types.Operator):
    bl_idname = "ai_copilot.install"
    bl_label = "Install OpenCode"
    bl_description = "Download and unpack the portable OpenCode runtime (~80 MB)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return not installer.installing()

    def execute(self, context):
        if installer.is_installed():
            self.report({'WARNING'}, "OpenCode is already installed")
            return {'CANCELLED'}
        installer.start_install()
        bpy.app.timers.register(_poll_install, first_interval=0.5)
        return {'FINISHED'}


def _poll_install():
    context = bpy.context
    ai = context.scene.ai
    state = installer.status()
    ai.oc_status = state["status"]
    ai.oc_progress = state["progress"]
    if installer.installing():
        return 0.5
    if state["status"] == "error":
        ai.oc_status = "error: %s" % state["error"]
    else:
        ai.oc_status = "installed (%s)" % state["version"]
    utils.redraw_all(context)
    return None


class AICopilotServerStart(bpy.types.Operator):
    bl_idname = "ai_copilot.server_start"
    bl_label = "Start Server"
    bl_description = "Start the local OpenCode server"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return installer.is_installed()

    def execute(self, context):
        ai = context.scene.ai
        if server.running() or server.is_up(ai.oc_port):
            ai.oc_status = "ready"
            return {'FINISHED'}
        ai.oc_status = "starting server..."
        utils.redraw_all(context)

        result = {}

        def worker():
            try:
                server.start(ai.oc_port, ai.oc_provider, ai.oc_api_key)
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        _SERVER["thread"] = thread
        _SERVER["result"] = result
        bpy.app.timers.register(_poll_server, first_interval=0.5)
        return {'FINISHED'}


def _poll_server():
    context = bpy.context
    ai = context.scene.ai
    thread = _SERVER.get("thread")
    if thread is not None and thread.is_alive():
        return 0.5
    result = _SERVER.pop("result", {})
    _SERVER["thread"] = None
    error = result.get("error")
    if error:
        ai.oc_status = "error: %s" % error
    elif server.running() or server.is_up(ai.oc_port):
        ai.oc_status = "ready"
    else:
        ai.oc_status = "failed to start"
    utils.redraw_all(context)
    return None


class AICopilotServerStop(bpy.types.Operator):
    bl_idname = "ai_copilot.server_stop"
    bl_label = "Stop Server"
    bl_description = "Stop the local OpenCode server"
    bl_options = {'REGISTER'}

    def execute(self, context):
        server.stop()
        context.scene.ai.oc_status = "stopped"
        utils.redraw_all(context)
        return {'FINISHED'}


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
    bl_description = "Send the message (and attached image) to the agent"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ai = getattr(context.scene, "ai", None)
        return ai is not None and not ai.busy and bool(ai.input.strip())

    def execute(self, context):
        ai = context.scene.ai
        if not server.running() and not server.is_up(ai.oc_port):
            self.report({'ERROR'}, "OpenCode server is not running. Start it in the status panel.")
            return {'CANCELLED'}

        text = ai.input.strip()
        image = ai.image_path if os.path.isfile(ai.image_path) else ""
        utils.add_message(context, "user", text, image)
        prompts.write_workspace_files(installer.workspace_dir(), context.scene, image)
        ai.input = ""
        ai.image_path = ""
        ai.busy = True
        utils.redraw_all(context)

        _start_http(text, image)
        bpy.app.timers.register(_poll_send, first_interval=0.5)
        return {'FINISHED'}


def _start_http(text, image):
    context = bpy.context
    ai = context.scene.ai
    result = {}

    def worker():
        try:
            sid, reply = server.chat(
                ai.oc_port,
                ai.oc_session_id,
                ai.oc_provider,
                ai.oc_model,
                text,
                image,
            )
            result["session"] = sid
            result["reply"] = reply
        except Exception as exc:
            result["error"] = str(exc)

    thread = threading.Thread(target=worker, daemon=True)
    _JOB["thread"] = thread
    _JOB["result"] = result
    _JOB["attempts"] = _JOB.get("attempts", 0) + 1
    thread.start()


def _run_blocks(context, blocks):
    ok, stdout, errlog = False, "", ""
    for code in blocks:
        ok, stdout, errlog = executor.run_code(code)
        if not ok:
            break
    return ok, stdout, errlog


def _poll_send():
    thread = _JOB.get("thread")
    if thread is not None and thread.is_alive():
        return 0.5

    result = _JOB.pop("result", {})
    thread = _JOB.pop("thread", None)
    attempts = _JOB.pop("attempts", 1)

    context = bpy.context
    ai = context.scene.ai

    error = result.get("error")
    if error:
        utils.add_message(context, "assistant", "Error: %s" % error)
        ai.busy = False
        utils.redraw_all(context)
        return None

    ai.oc_session_id = result.get("session", ai.oc_session_id)
    reply = result.get("reply", "")
    if not reply:
        utils.add_message(context, "assistant", "Error: the agent returned an empty response")
        ai.busy = False
        utils.redraw_all(context)
        return None

    utils.add_message(context, "assistant", reply)
    blocks = utils.extract_code(reply)

    if not ai.auto_run or not blocks:
        ai.busy = False
        utils.redraw_all(context)
        return None

    ok, stdout, errlog = _run_blocks(context, blocks)
    if ok:
        if stdout.strip():
            text = "Code executed. Output:\n%s" % utils.truncate(stdout.strip())
        else:
            text = "Code executed successfully."
        utils.add_message(context, "assistant", "[run] " + text)
        ai.busy = False
    elif ai.oc_auto_fix and attempts < 3:
        log = utils.truncate((stdout.strip() + "\n" + errlog.strip()).strip())
        fix_text = (
            "Your script failed with this log:\n\n%s\n\n"
            "Return one corrected complete Python script." % log
        )
        utils.add_message(context, "user", "[auto-fix] " + fix_text)
        _start_http(fix_text, "")
        utils.redraw_all(context)
        return 0.5
    else:
        utils.add_message(
            context,
            "assistant",
            "[run] Execution failed:\n%s" % utils.truncate(errlog.strip()),
        )
        ai.busy = False

    utils.redraw_all(context)
    return None


class AICopilotRunLast(bpy.types.Operator):
    bl_idname = "ai_copilot.run_last"
    bl_label = "Run Last Code"
    bl_description = "Re-run the code from the last agent response"
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
                    ok, stdout, errlog = _run_blocks(context, blocks)
                    if ok:
                        text = "Code executed. Output:\n%s" % utils.truncate(stdout.strip()) if stdout.strip() else "Code executed successfully."
                    else:
                        text = "Execution failed:\n%s" % utils.truncate(errlog.strip())
                    utils.add_message(context, "assistant", "[run] " + text)
                    utils.redraw_all(context)
                    return {'FINISHED'}
        return {'CANCELLED'}


class AICopilotClear(bpy.types.Operator):
    bl_idname = "ai_copilot.clear"
    bl_label = "Clear Chat"
    bl_description = "Clear the conversation and start a new agent session"
    bl_options = {'REGISTER'}

    def execute(self, context):
        ai = context.scene.ai
        if server.running() or server.is_up(ai.oc_port):
            server.delete_session(ai.oc_port, ai.oc_session_id)
        ai.oc_session_id = ""
        ai.messages.clear()
        utils.redraw_all(context)
        return {'FINISHED'}


classes = (
    AICopilotInstall,
    AICopilotServerStart,
    AICopilotServerStop,
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
    server.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
