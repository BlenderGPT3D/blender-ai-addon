import contextlib
import io
import traceback

import bmesh
import bpy
import math
import mathutils
import random


def run_code(code):
    stdout = io.StringIO()
    env = {
        "bpy": bpy,
        "bmesh": bmesh,
        "mathutils": mathutils,
        "math": math,
        "random": random,
        "__name__": "ai_copilot_exec",
    }
    try:
        with contextlib.redirect_stdout(stdout):
            exec(compile(code, "<ai_copilot>", "exec"), env)
        return True, stdout.getvalue(), ""
    except Exception:
        return False, stdout.getvalue(), traceback.format_exc(limit=6)
