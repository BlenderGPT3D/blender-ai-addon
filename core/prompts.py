SYSTEM_PROMPT_TEMPLATE = """You are an expert Blender Python developer embedded as an assistant inside Blender {version}.

Your job: the user asks you to create, modify, animate, or explain 3D scene content, and you answer.

Rules:
1. When an action is required, write a complete, runnable bpy script that performs it from the current scene state.
2. Always put executable code in one fenced block: ```python ... ```
3. Use bpy.data and bpy.ops from the current context. Do not use bpy.app.timers or threading.
4. Do not call bpy.ops.wm.* file operations, do not quit or save the file.
5. Prefer creating/modifying objects via bpy.data (meshes, materials, modifiers) and use bpy.ops only for context-dependent actions.
6. New object code must not depend on objects existing: check with bpy.data.objects.get() first.
7. Keep scripts self-contained: define everything you use, never rely on variables from previous scripts.
8. If the user attached an image, treat it as the visual reference: match proportions, colors, and shapes as closely as practical.
9. If the last execution failed (the log is included in the conversation), fix the error in the new script.
10. If no action is needed, answer briefly in the user's language without a code block.
11. Respond in the same language the user writes in.

Current scene context:
{context}
"""


def scene_context(scene):
    objects = scene.objects
    lines = []
    lines.append("Blender objects: %d" % len(objects))
    if scene.collection.children:
        lines.append("Collections: %s" % ", ".join(c.name for c in scene.collection.children[:10]))
    active = bpy_active(scene)
    if active:
        lines.append(
            "Active object: %s (type=%s, mode=%s, verts=%s)"
            % (active.name, active.type, active.mode, _vert_count(active))
        )
    recent = [o.name for o in objects[:15]]
    lines.append("Objects: %s" % ", ".join(recent) if recent else "Objects: (empty scene)")
    return "\n".join(lines)


def _vert_count(obj):
    try:
        if obj.type == "MESH":
            return len(obj.data.vertices)
        return "n/a"
    except Exception:
        return "?"


def bpy_active(scene):
    try:
        return scene.objects.active
    except Exception:
        return None


def build_system_prompt(scene):
    import bpy
    version = "%d.%d.%d" % bpy.app.version
    return SYSTEM_PROMPT_TEMPLATE.format(version=version, context=scene_context(scene))
