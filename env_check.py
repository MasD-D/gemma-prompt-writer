import json
import shutil
import subprocess
import time
from pathlib import Path

import requests


OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_PULL_URL = "http://localhost:11434/api/pull"
MODEL_NAME = "gemma4:12b"


def find_ollama_binary():
    path = shutil.which("ollama")
    if path:
        return path

    candidates = [
        "/opt/homebrew/bin/ollama",
        "/usr/local/bin/ollama",
        "/Applications/Ollama.app/Contents/Resources/ollama"
    ]

    for item in candidates:
        if Path(item).exists():
            return item

    return None


def is_ollama_service_running():
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama_service():
    ollama_bin = find_ollama_binary()

    if not ollama_bin:
        return False, "未找到 ollama 命令。"

    if is_ollama_service_running():
        return True, "Ollama 服务已运行。"

    try:
        subprocess.Popen(
            [ollama_bin, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        return False, f"启动 Ollama 失败：{e}"

    for _ in range(30):
        if is_ollama_service_running():
            return True, "Ollama 服务已启动。"
        time.sleep(1)

    return False, "Ollama 服务启动超时。"


def list_ollama_models():
    if not is_ollama_service_running():
        return []

    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def has_model(model_name=MODEL_NAME):
    models = list_ollama_models()
    return model_name in models


def check_environment(model_name=MODEL_NAME):
    ollama_bin = find_ollama_binary()
    service_running = is_ollama_service_running()
    models = list_ollama_models() if service_running else []

    return {
        "ollama_installed": bool(ollama_bin),
        "ollama_path": ollama_bin or "",
        "ollama_service_running": service_running,
        "target_model": model_name,
        "model_installed": model_name in models,
        "models": models
    }


def pull_model(model_name=MODEL_NAME, progress_callback=None):
    payload = {
        "model": model_name,
        "stream": True
    }

    with requests.post(
        OLLAMA_PULL_URL,
        json=payload,
        stream=True,
        timeout=None
    ) as r:
        r.raise_for_status()

        last_status = ""

        for line in r.iter_lines():
            if not line:
                continue

            try:
                data = json.loads(line.decode("utf-8"))
            except Exception:
                continue

            status = data.get("status", "")
            completed = data.get("completed")
            total = data.get("total")

            if completed and total:
                percent = completed / total * 100
                message = f"{status}：{percent:.1f}%"
            else:
                message = status or str(data)

            if message and message != last_status:
                last_status = message
                if progress_callback:
                    progress_callback(message)

            if status == "success":
                return True

    return has_model(model_name)


if __name__ == "__main__":
    print(json.dumps(check_environment(), ensure_ascii=False, indent=2))
