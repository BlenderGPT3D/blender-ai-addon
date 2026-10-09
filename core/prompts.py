AGENTS_TEMPLATE = """# Blender AI Copilot workspace

You are assisting a Blender user from inside a Blender add-on. The user cannot see
this workspace, only your replies.

## Output rules (mandatory)

1. Every reply that requires an action MUST contain ONE complete runnable Python
   script in a single fenced block: ```python ... ```
2. The script runs inside Blender with full access to `bpy`, `bmesh`, `mathutils`,
   `math`, `random`. It must be self-contained: never rely on variables or objects
   created by previous scripts.
3. Never use `bpy.app.timers`, `threading`, or `bpy.ops.wm.*` file dialogs.
   Never save, quit, or overwrite the user's file.
4. Prefer `bpy.data` (meshes, materials, modifiers, collections) over `bpy.ops`.
   Guard object creation with `bpy.data.objects.get(...)`.
5. Do NOT use the shell/bash tool: you cannot touch Blender from it. Do not edit
   files except scratch files in this workspace.
6. If the last execution failed (the log is pasted by the user), fix the error and
   return the corrected full script.
7. If no action is needed, answer briefly in the user's language without a code block.
8. Reply in the same language the user writes in.

## Workspace files

- `scene_context.txt` - fresh description of the current Blender scene, updated
  before every message. Read it before answering.
- `reference_image.png` - the image the user attached to the current message, if any.
  Match proportions, colors and shapes from it as closely as practical.
"""


def scene_context(scene):
    import bpy
    lines = []
    lines.append("Blender %d.%d.%d" % bpy.app.version[:3])
    lines.append("Objects: %d" % len(scene.objects))
    if scene.collection.children:
        lines.append(
            "Collections: %s" % ", ".join(c.name for c in scene.collection.children[:10])
        )
    active = _active_object(scene)
    if active:
        lines.append(
            "Active object: %s (type=%s, mode=%s, verts=%s)"
            % (active.name, active.type, active.mode, _vert_count(active))
        )
    names = [o.name for o in scene.objects[:15]]
    if names:
        lines.append("Object names: %s" % ", ".join(names))
    return "\n".join(lines)


def _active_object(scene):
    try:
        return scene.objects.active
    except Exception:
        return None


def _vert_count(obj):
    try:
        if obj.type == "MESH":
            return len(obj.data.vertices)
        return "n/a"
    except Exception:
        return "?"


def write_workspace_files(workspace, scene, image_path):
    import os
    import shutil

    with open(os.path.join(workspace, "AGENTS.md"), "w", encoding="utf-8") as fh:
        fh.write(AGENTS_TEMPLATE)
    with open(os.path.join(workspace, "scene_context.txt"), "w", encoding="utf-8") as fh:
        fh.write(scene_context(scene))
    ref = os.path.join(workspace, "reference_image.png")
    if image_path and os.path.isfile(image_path):
        try:
            shutil.copy(image_path, ref)
        except Exception:
            pass
    elif os.path.isfile(ref):
        try:
            os.remove(ref)
        except Exception:
            pass
