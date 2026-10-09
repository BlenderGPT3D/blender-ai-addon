import re

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(text):
    return CODE_RE.findall(text or "")


def wrap_text(text, width=56):
    lines = []
    for raw in (text or "").splitlines() or [""]:
        while len(raw) > width:
            lines.append(raw[:width])
            raw = raw[width:]
        lines.append(raw)
    return lines


def add_message(context, role, content, image=""):
    msg = context.scene.ai.messages.add()
    msg.role = role
    msg.content = content
    msg.image = image
    return msg


def redraw_all(context=None):
    import bpy
    wm = context.window_manager if context else bpy.context.window_manager
    for window in wm.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def truncate(text, limit=2000):
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (truncated)"
