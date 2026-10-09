import json
import os
import platform
import subprocess
import time

import requests

from . import opencode_installer as installer

PROC = None
_LOG = None

PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "ollama": "",
    "custom": "OPENAI_API_KEY",
}


class ServerError(Exception):
    pass


def base_url(port):
    return "http://127.0.0.1:%d" % port


def is_up(port):
    try:
        response = requests.get(base_url(port) + "/session", timeout=2)
        return response.status_code < 500
    except requests.RequestException:
        return False


def write_config(provider):
    cfg_dir = os.path.join(installer.config_dir(), "opencode")
    os.makedirs(cfg_dir, exist_ok=True)
    config = {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "permission": {
            "bash": "deny",
            "edit": "allow",
            "webfetch": "allow",
        },
    }
    with open(os.path.join(cfg_dir, "opencode.json"), "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


def start(port, provider, api_key):
    global PROC, _LOG
    if PROC is not None and PROC.poll() is None:
        return True
    binary = installer.binary_path()
    if not binary:
        raise ServerError("OpenCode is not installed")
    if is_up(port):
        return True
    write_config(provider)
    env = os.environ.copy()
    env["XDG_CONFIG_HOME"] = installer.config_dir()
    env["XDG_DATA_HOME"] = installer.home_data_dir()
    env_key = PROVIDER_ENV.get(provider, "")
    if env_key and api_key:
        env[env_key] = api_key
    log_path = os.path.join(installer.data_root(), "server.log")
    _LOG = open(log_path, "ab")
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if platform.system() == "Windows" else {}
    PROC = subprocess.Popen(
        [binary, "serve", "--port", str(port), "--hostname", "127.0.0.1"],
        cwd=installer.workspace_dir(),
        env=env,
        stdout=_LOG,
        stderr=subprocess.STDOUT,
        **kwargs,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        if PROC.poll() is not None:
            raise ServerError("OpenCode exited during startup, see server.log")
        if is_up(port):
            return True
        time.sleep(1.0)
    raise ServerError("OpenCode server did not start in 60s")


def stop():
    global PROC, _LOG
    if PROC is not None:
        try:
            PROC.terminate()
            PROC.wait(timeout=5)
        except Exception:
            try:
                PROC.kill()
            except Exception:
                pass
    PROC = None
    if _LOG is not None:
        try:
            _LOG.close()
        except Exception:
            pass
        _LOG = None


def running():
    return PROC is not None and PROC.poll() is None


def _create_session(port):
    response = requests.post(base_url(port) + "/session", json={"title": "Blender AI Copilot"}, timeout=30)
    response.raise_for_status()
    return response.json()["id"]


def _message_parts(text, image_path):
    parts = [{"type": "text", "text": text}]
    if image_path and os.path.isfile(image_path):
        uri = installer_image_uri(image_path)
        if uri:
            parts.append({"type": "file", "mime": uri[0], "url": uri[1]})
    return parts


def installer_image_uri(path):
    import base64
    import mimetypes
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        raw = fh.read()
    return mime, "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


def _parts_to_text(parts):
    chunks = []
    for part in parts or []:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            chunks.append(part["text"])
    return "\n".join(chunks).strip()


def _fetch_last_assistant(port, session_id):
    response = requests.get(
        base_url(port) + "/session/%s/message?limit=10" % session_id, timeout=30
    )
    response.raise_for_status()
    for item in reversed(response.json() or []):
        info = item.get("info", {})
        if info.get("role") == "assistant":
            return _parts_to_text(item.get("parts", []))
    return ""


def chat(port, session_id, provider, model, text, image_path):
    full_model = model if "/" in model else "%s/%s" % (provider, model)
    provider_id = full_model.split("/", 1)[0]
    model_id = full_model.split("/", 1)[1]
    body = {
        "parts": _message_parts(text, image_path),
        "model": {"providerID": provider_id, "modelID": model_id},
    }
    sid = session_id
    for attempt in range(2):
        if not sid:
            sid = _create_session(port)
        response = requests.post(
            base_url(port) + "/session/%s/message" % sid,
            json=body,
            timeout=1800,
        )
        if response.status_code == 404 and attempt == 0:
            sid = ""
            continue
        response.raise_for_status()
        break
    try:
        data = response.json()
        reply = _parts_to_text(data.get("parts", []))
    except Exception:
        reply = ""
    if not reply:
        reply = _fetch_last_assistant(port, sid)
    return sid, reply


def delete_session(port, session_id):
    if not session_id:
        return
    try:
        requests.delete(base_url(port) + "/session/%s" % session_id, timeout=15)
    except requests.RequestException:
        pass
