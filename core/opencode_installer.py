import json
import os
import platform
import shutil
import stat
import tarfile
import threading
import zipfile

import bpy
import requests

RELEASE_API = "https://api.github.com/repos/anomalyco/opencode/releases/latest"

_state = {"status": "not installed", "progress": 0.0, "error": "", "version": ""}


def data_root():
    return bpy.utils.user_resource("DATAFILES", path="ai_copilot", create=True)


def install_dir():
    path = os.path.join(data_root(), "runtime")
    os.makedirs(path, exist_ok=True)
    return path


def workspace_dir():
    path = os.path.join(data_root(), "workspace")
    os.makedirs(path, exist_ok=True)
    return path


def config_dir():
    return os.path.join(data_root(), "config")


def home_data_dir():
    path = os.path.join(data_root(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def binary_path():
    exe = "opencode.exe" if platform.system() == "Windows" else "opencode"
    path = os.path.join(install_dir(), exe)
    return path if os.path.isfile(path) else ""


def is_installed():
    return bool(binary_path())


def status():
    return dict(_state)


def _platform_slug():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        return "windows-arm64" if ("arm" in machine or "aarch" in machine) else "windows-x64"
    if system == "Darwin":
        return "darwin-arm64" if machine in ("arm64", "aarch64") else "darwin-x64"
    return "linux-arm64" if machine in ("arm64", "aarch64") else "linux-x64"


def _pick_asset(assets):
    slug = _platform_slug()
    for asset in assets:
        name = asset.get("name", "")
        if slug in name and name.endswith((".zip", ".tar.gz", ".tgz")):
            return asset
    return None


def latest_release():
    response = requests.get(RELEASE_API, timeout=30, headers={"Accept": "application/vnd.github+json"})
    response.raise_for_status()
    data = response.json()
    asset = _pick_asset(data.get("assets", []))
    if not asset:
        raise RuntimeError("No OpenCode build for platform %s" % _platform_slug())
    return data.get("tag_name", "?"), asset["browser_download_url"], asset["name"]


def _extract(archive_path, dest):
    if archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(archive_path) as tf:
            tf.extractall(dest)


def _locate_binary(dest):
    exe = "opencode.exe" if platform.system() == "Windows" else "opencode"
    root = os.path.join(dest, exe)
    if os.path.isfile(root):
        return root
    for dirpath, _dirnames, filenames in os.walk(dest):
        if exe in filenames:
            return os.path.join(dirpath, exe)
    return ""


def _finalize_binary(found):
    target = os.path.join(install_dir(), os.path.basename(found))
    if os.path.abspath(found) != os.path.abspath(target):
        shutil.move(found, target)
    if platform.system() != "Windows":
        mode = os.stat(target).st_mode
        os.chmod(target, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return target


def _install_worker():
    try:
        _state.update(status="checking release...", progress=0.0, error="", version="")
        tag, url, name = latest_release()
        _state["version"] = tag
        archive = os.path.join(data_root(), name)
        _state["status"] = "downloading..."
        with requests.get(url, stream=True, timeout=600) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            done = 0
            with open(archive, "wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    fh.write(chunk)
                    done += len(chunk)
                    if total:
                        _state["progress"] = min(1.0, done / total)
        _state["status"] = "unpacking..."
        _extract(archive, install_dir())
        os.remove(archive)
        found = _locate_binary(install_dir())
        if not found:
            raise RuntimeError("opencode binary not found in the archive")
        _finalize_binary(found)
        _state.update(status="installed", progress=1.0)
    except Exception as exc:
        _state.update(status="error", error=str(exc))


def start_install():
    if _state.get("thread") and _state["thread"].is_alive():
        return False
    thread = threading.Thread(target=_install_worker, daemon=True)
    _state["thread"] = thread
    thread.start()
    return True


def installing():
    thread = _state.get("thread")
    return thread is not None and thread.is_alive()
