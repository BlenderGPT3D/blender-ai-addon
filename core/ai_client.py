import base64
import json
import mimetypes
import os

import requests

DEFAULT_TIMEOUT = 180


class AIError(Exception):
    pass


def image_to_data_uri(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        raw = fh.read()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(raw).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


def _user_content(text, image_path):
    uri = image_to_data_uri(image_path)
    if not uri:
        return text
    return [
        {"type": "text", "text": text or "Use this image as reference."},
        {"type": "image_url", "image_url": {"url": uri}},
    ]


def build_payload(history, system_prompt, limit=24):
    payload = [{"role": "system", "content": system_prompt}]
    for msg in history[-limit:]:
        if msg.role == "user":
            content = _user_content(msg.content, msg.image)
        elif msg.role == "assistant":
            content = msg.content
        else:
            continue
        if not content:
            continue
        payload.append({"role": msg.role, "content": content})
    return payload


def send_chat(base_url, api_key, model, messages, temperature=0.2, max_tokens=2048):
    if not api_key:
        raise AIError("API key is not set. Open the Settings panel and paste your key.")
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": "Bearer %s" % api_key,
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body), timeout=DEFAULT_TIMEOUT)
    except requests.RequestException as exc:
        raise AIError("Connection failed: %s" % exc)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except Exception:
            detail = response.text[:300]
        raise AIError("API error %s: %s" % (response.status_code, detail))
    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise AIError("Unexpected API response: %s" % response.text[:300])
