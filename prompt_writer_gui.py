import json
import sys
import re
import time
import shutil
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import requests
import env_check
import hardware_check
import model_advisor


APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Gemma Prompt Writer"
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_SUPPORT_DIR / "config.json"
LOG_FILE = APP_SUPPORT_DIR / "app.log"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

DEFAULT_MODEL_NAME = "gemma4:12b"


def resource_path(relative_path: str) -> Path:
    """
    Resolve resource paths both in source mode and PyInstaller app mode.
    """
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path


PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "prompt_en": {"type": "string"},
                    "prompt_zh": {"type": "string"},
                    "negative_prompt": {"type": "string"},
                    "usage_note": {"type": "string"}
                },
                "required": [
                    "title",
                    "prompt_en",
                    "prompt_zh",
                    "negative_prompt",
                    "usage_note"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["prompts"],
    "additionalProperties": False
}


def log_error(message: str):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat()}]\n{message}\n")
    except Exception:
        pass


def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log_error(f"读取配置失败：{e}")

    return {
        "model_name": DEFAULT_MODEL_NAME,
        "obsidian_output_dir": ""
    }


def save_config(config):
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


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



def find_obsidian_app():
    """
    Detect Obsidian.app on macOS.
    """
    candidates = [
        Path("/Applications/Obsidian.app"),
        Path.home() / "Applications" / "Obsidian.app",
    ]

    for item in candidates:
        if item.exists():
            return str(item)

    try:
        result = subprocess.check_output(
            ["mdfind", "kMDItemCFBundleIdentifier == 'md.obsidian'"],
            text=True,
            timeout=5
        ).strip()

        if result:
            for line in result.splitlines():
                if line.endswith("Obsidian.app") and Path(line).exists():
                    return line
    except Exception:
        pass

    return ""

def ensure_ollama_running(status_callback):
    try:
        requests.get(OLLAMA_TAGS_URL, timeout=3)
        return True
    except Exception:
        pass

    ollama_bin = find_ollama_binary()
    if not ollama_bin:
        raise RuntimeError("没有找到 Ollama。请先安装 Ollama，然后重新打开本 App。")

    status_callback("未检测到 Ollama 服务，正在尝试启动本地 Ollama...")

    subprocess.Popen(
        [ollama_bin, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(30):
        try:
            requests.get(OLLAMA_TAGS_URL, timeout=3)
            return True
        except Exception:
            time.sleep(1)

    raise RuntimeError("Ollama 服务启动超时。可以先手动运行：ollama serve")


def extract_json(raw: str):
    text = raw.strip()

    if "<|tool_response>" in text:
        text = text.split("<|tool_response>")[0].strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError(f"无法从模型输出中提取 JSON：\n{text}")


def build_prompt(user_idea: str, count: int, style_hint: str, platform_hint: str):
    return f"""
你是一个专业图像生成提示词工程师。

用户会输入一个画面想法。你需要把它扩展成 {count} 段高质量生图提示词。

输出要求：
1. 只输出 JSON。
2. 不要输出 thought。
3. 不要输出 reasoning。
4. 不要输出 markdown。
5. 顶层 JSON 只能包含 prompts 字段。
6. 每条提示词都要有明显差异。
7. 每条提示词都要适合直接复制到生图工具中使用。
8. 英文 prompt 要更完整、更适合生图模型。
9. 中文 prompt 要便于用户理解和二次修改。
10. negative_prompt 要包含常见负面约束。
11. usage_note 用中文说明这条提示词适合什么场景。
12. 避免直接使用具体商业工作室风格名称，例如 Pixar、Disney、Ghibli、Marvel、Apple 等。

用户想法：
{user_idea}

风格补充：
{style_hint}

目标平台或用途：
{platform_hint}

请输出如下 JSON 结构：

{{
  "prompts": [
    {{
      "title": "提示词标题",
      "prompt_en": "English image generation prompt",
      "prompt_zh": "中文生图提示词",
      "negative_prompt": "low quality, blurry, watermark...",
      "usage_note": "这条适合用于..."
    }}
  ]
}}
"""


def call_gemma(model_name, user_idea, count, style_hint, platform_hint, status_callback):
    prompt = build_prompt(user_idea, count, style_hint, platform_hint)

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "format": PROMPT_SCHEMA,
        "think": False,
        "options": {
            "temperature": 0.75,
            "top_p": 0.9,
            "num_predict": 8000
        }
    }

    status_callback("正在调用本地 Gemma 生成提示词...")

    response = requests.post(OLLAMA_URL, json=payload, timeout=300)

    if response.status_code >= 400:
        raise RuntimeError(response.text)

    raw = response.json().get("response", "")
    data = extract_json(raw)

    if not isinstance(data, dict) or "prompts" not in data:
        raise ValueError("Gemma 没有返回 prompts 字段。")

    return data["prompts"]


def safe_filename(text):
    text = text.strip()
    text = re.sub(r"[\\/:*?\"<>|#$begin:math:display$$end:math:display$]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:24] or "生图提示词"


def build_markdown(user_idea, style_hint, platform_hint, prompts):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("---")
    lines.append("type: image-prompt")
    lines.append("source: local-gemma")
    lines.append(f"created: {now}")
    lines.append("tags:")
    lines.append("  - 生图提示词")
    lines.append("  - Gemma")
    lines.append("---")
    lines.append("")
    lines.append(f"# 生图提示词｜{safe_filename(user_idea)}")
    lines.append("")
    lines.append(f"生成时间：{now}")
    lines.append("")
    lines.append(f"原始想法：{user_idea}")
    lines.append("")
    lines.append(f"风格补充：{style_hint}")
    lines.append("")
    lines.append(f"目标平台或用途：{platform_hint}")
    lines.append("")

    for idx, item in enumerate(prompts, start=1):
        lines.append("---")
        lines.append("")
        lines.append(f"## {idx}. {item['title']}")
        lines.append("")
        lines.append("### 英文 Prompt")
        lines.append("")
        lines.append(item["prompt_en"])
        lines.append("")
        lines.append("### 中文 Prompt")
        lines.append("")
        lines.append(item["prompt_zh"])
        lines.append("")
        lines.append("### Negative Prompt")
        lines.append("")
        lines.append(item["negative_prompt"])
        lines.append("")
        lines.append("### 使用建议")
        lines.append("")
        lines.append(item["usage_note"])
        lines.append("")

    return "\n".join(lines)


def save_to_obsidian(output_dir, user_idea, markdown):
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    date_part = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_part = safe_filename(user_idea)
    file_path = output_path / f"{date_part}_{name_part}.md"

    file_path.write_text(markdown, encoding="utf-8")
    return file_path


class PromptWriterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemma 生图提示词生成器")
        self.root.geometry("1040x860")

        icon_path = resource_path("assets/app_icon_256.png")
        if icon_path.exists():
            try:
                self.window_icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, self.window_icon)
            except Exception as e:
                log_error(f"设置窗口图标失败：{e}")

        self.config = load_config()

        self.model_var = tk.StringVar(value=self.config.get("model_name", DEFAULT_MODEL_NAME))
        self.output_dir_var = tk.StringVar(value=self.config.get("obsidian_output_dir", ""))

        self.env_ready = False

        self.create_widgets()
        self.root.after(300, self.refresh_environment)

    def create_widgets(self):
        pad = 10

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=pad, pady=(pad, 4))

        tk.Label(top_frame, text="模型：").pack(side="left")
        tk.Entry(top_frame, textvariable=self.model_var, width=20).pack(side="left", padx=(0, 12))

        tk.Label(top_frame, text="Markdown 保存目录（可选）：").pack(side="left")
        tk.Entry(top_frame, textvariable=self.output_dir_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(top_frame, text="选择目录", command=self.choose_output_dir).pack(side="left")

        env_frame = tk.LabelFrame(self.root, text="环境自检")
        env_frame.pack(fill="x", padx=pad, pady=6)

        self.env_status_var = tk.StringVar(value="正在检测环境...")
        tk.Label(env_frame, textvariable=self.env_status_var, anchor="w", justify="left").pack(
            fill="x",
            padx=pad,
            pady=(8, 6)
        )

        env_button_frame = tk.Frame(env_frame)
        env_button_frame.pack(fill="x", padx=pad, pady=(0, 8))

        tk.Button(env_button_frame, text="刷新自检", command=self.refresh_environment).pack(side="left", padx=(0, 8))
        tk.Button(env_button_frame, text="检查 Ollama 状态", command=self.open_ollama_status_checker).pack(side="left", padx=(0, 8))
        tk.Button(env_button_frame, text="推荐 Gemma 模型", command=self.open_model_advisor).pack(side="left", padx=(0, 8))
        tk.Button(env_button_frame, text="检查 Obsidian 状态", command=self.open_obsidian_status_checker).pack(side="left")

        idea_frame = tk.LabelFrame(self.root, text="画面想法")
        idea_frame.pack(fill="both", padx=pad, pady=6)

        self.idea_text = scrolledtext.ScrolledText(idea_frame, height=6, wrap="word")
        self.idea_text.pack(fill="both", expand=True, padx=pad, pady=pad)

        options_frame = tk.Frame(self.root)
        options_frame.pack(fill="x", padx=pad, pady=6)

        tk.Label(options_frame, text="数量：").pack(side="left")
        self.count_var = tk.IntVar(value=5)
        tk.Spinbox(options_frame, from_=3, to=5, textvariable=self.count_var, width=5).pack(side="left", padx=(0, 16))

        tk.Label(options_frame, text="风格补充：").pack(side="left")
        self.style_var = tk.StringVar(value="高质量、画面干净、构图明确、有商业完成度")
        tk.Entry(options_frame, textvariable=self.style_var, width=42).pack(side="left", padx=(0, 16))

        tk.Label(options_frame, text="用途：").pack(side="left")
        self.platform_var = tk.StringVar(value="通用生图工具")
        tk.Entry(options_frame, textvariable=self.platform_var, width=24).pack(side="left")

        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=pad, pady=6)

        self.generate_button = tk.Button(
            action_frame,
            text="生成提示词",
            command=self.generate
        )
        self.generate_button.pack(side="left")

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(action_frame, textvariable=self.status_var, anchor="w").pack(side="left", padx=12)

        result_frame = tk.LabelFrame(self.root, text="生成结果")
        result_frame.pack(fill="both", expand=True, padx=pad, pady=(6, pad))

        result_action_frame = tk.Frame(result_frame)
        result_action_frame.pack(fill="x", padx=pad, pady=(pad, 0))

        tk.Button(
            result_action_frame,
            text="复制生成结果",
            command=self.copy_result_to_clipboard
        ).pack(side="left")

        self.result_text = scrolledtext.ScrolledText(result_frame, wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=pad, pady=pad)


    def copy_result_to_clipboard(self):
        content = self.result_text.get("1.0", tk.END).strip()

        if not content:
            messagebox.showinfo("暂无内容", "当前没有可复制的生成结果。")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()
        self.set_status("生成结果已复制到剪贴板。")


    def choose_output_dir(self):
        directory = filedialog.askdirectory(title="选择 Obsidian 中的保存目录")
        if directory:
            self.output_dir_var.set(directory)
            self.save_current_config()

    def save_current_config(self):
        self.config["model_name"] = self.model_var.get().strip() or DEFAULT_MODEL_NAME
        self.config["obsidian_output_dir"] = self.output_dir_var.get().strip()
        save_config(self.config)

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def set_env_status(self, text):
        self.root.after(0, lambda: self.env_status_var.set(text))

    def set_result(self, text):
        def update():
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, text)
        self.root.after(0, update)

    def format_env_result(self, result):
        ollama_status = "已安装" if result["ollama_installed"] else "未安装"
        service_status = "已运行" if result["ollama_service_running"] else "未运行"
        model_status = "已安装" if result["model_installed"] else "未安装"

        lines = [
            f"Ollama：{ollama_status}",
            f"Ollama 路径：{result['ollama_path'] or '未检测到'}",
            f"Ollama 服务：{service_status}",
            f"目标模型：{result['target_model']}",
            f"模型状态：{model_status}"
        ]

        if result["models"]:
            lines.append("已安装模型：" + ", ".join(result["models"]))

        return "\n".join(lines)

    def refresh_environment(self):
        def worker():
            try:
                model_name = self.model_var.get().strip() or DEFAULT_MODEL_NAME
                result = env_check.check_environment(model_name)
                self.env_ready = (
                    result["ollama_installed"]
                    and result["ollama_service_running"]
                    and result["model_installed"]
                )

                self.set_env_status(self.format_env_result(result))

                if self.env_ready:
                    self.set_status("环境正常，可以生成。")
                else:
                    self.set_status("环境未就绪，请根据自检结果处理。")

            except Exception as e:
                self.env_ready = False
                log_error(f"环境自检失败：{e}")
                self.set_env_status(f"环境自检失败：{e}")
                self.set_status("环境自检失败")

        threading.Thread(target=worker, daemon=True).start()

    def start_ollama(self):
        def worker():
            try:
                self.set_status("正在启动 Ollama...")
                ok, msg = env_check.start_ollama_service()
                self.set_status(msg)
                self.refresh_environment()

                if not ok:
                    messagebox.showwarning("启动 Ollama 失败", msg)

            except Exception as e:
                log_error(f"启动 Ollama 失败：{e}")
                self.set_status("启动 Ollama 失败")
                messagebox.showerror("启动 Ollama 失败", str(e))

        threading.Thread(target=worker, daemon=True).start()



    def open_ollama_status_checker(self):
        checker_window = tk.Toplevel(self.root)
        checker_window.title("Ollama 状态检查")
        checker_window.geometry("680x420")

        result_box = scrolledtext.ScrolledText(checker_window, wrap="word", height=14)
        result_box.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        button_frame = tk.Frame(checker_window)
        button_frame.pack(fill="x", padx=10, pady=(4, 10))

        ollama_path = env_check.find_ollama_binary()
        service_running = env_check.is_ollama_service_running()

        lines = []
        lines.append("Ollama 状态检查")
        lines.append("-" * 40)

        if ollama_path:
            lines.append("检测结果：已检测到 Ollama")
            lines.append(f"Ollama 路径：{ollama_path}")
            lines.append(f"Ollama 服务：{'正在运行' if service_running else '未运行'}")
            lines.append("")
            lines.append("说明：")
            lines.append("Ollama 是本 App 调用本地 Gemma 模型所需的本地模型运行环境。")
            lines.append("如果 Ollama 已安装但服务未运行，可以点击下方“启动 Ollama”。")
        else:
            lines.append("检测结果：未检测到 Ollama")
            lines.append("")
            lines.append("说明：")
            lines.append("本 App 需要通过 Ollama 调用本地 Gemma 模型。")
            lines.append("请先安装 Ollama。安装后回到本 App，点击“刷新自检”或重新检查状态。")

        result_box.insert(tk.END, "\n".join(lines))
        result_box.config(state="disabled")

        if ollama_path and not service_running:
            tk.Button(
                button_frame,
                text="启动 Ollama",
                command=lambda: [checker_window.destroy(), self.start_ollama()]
            ).pack(side="left", padx=(0, 8))

        if not ollama_path:
            tk.Button(
                button_frame,
                text="下载 Ollama",
                command=lambda: webbrowser.open("https://ollama.com/download")
            ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="重新检查",
            command=lambda: [checker_window.destroy(), self.open_ollama_status_checker()]
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="关闭",
            command=checker_window.destroy
        ).pack(side="right")

    def open_obsidian_status_checker(self):
        checker_window = tk.Toplevel(self.root)
        checker_window.title("Obsidian 状态检查")
        checker_window.geometry("720x520")

        result_box = scrolledtext.ScrolledText(checker_window, wrap="word", height=18)
        result_box.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        button_frame = tk.Frame(checker_window)
        button_frame.pack(fill="x", padx=10, pady=(4, 10))

        obsidian_path = find_obsidian_app()
        current_output_dir = self.output_dir_var.get().strip()

        lines = []
        lines.append("Obsidian 状态检查")
        lines.append("-" * 40)

        if obsidian_path:
            lines.append("检测结果：已检测到 Obsidian")
            lines.append(f"Obsidian 路径：{obsidian_path}")
        else:
            lines.append("检测结果：未检测到 Obsidian")

        lines.append("")
        lines.append("当前保存目录：")
        lines.append(current_output_dir if current_output_dir else "尚未选择")
        lines.append("")
        lines.append("使用方法：")
        lines.append("1. Obsidian 是可选的；不安装 Obsidian 也可以生成提示词。")
        lines.append("2. 如果不选择保存目录，生成结果只会显示在窗口中，不会自动保存为文件，请尽快复制。")
        lines.append("3. 本 App 不直接写入 Obsidian 应用本身，而是把 Markdown 文件写入你选择的文件夹。")
        lines.append("4. 这个文件夹可以是你的 Obsidian Vault 根目录，也可以是 Vault 里面的某个子文件夹。")
        lines.append("5. 选择保存目录后，生成的提示词会以 .md 文件形式保存进去。")
        lines.append("6. Obsidian 通常会自动显示这些新文件；如果没有显示，可以在 Obsidian 里刷新文件列表或重新打开 Vault。")
        lines.append("")
        lines.append("如何获取保存目录：")
        lines.append("1. 在 Finder 中找到你的 Obsidian Vault 文件夹。")
        lines.append("2. 或者在 Obsidian 中确认当前 Vault 的本地存储位置。")
        lines.append("3. 如果你想单独管理提示词，可以在 Vault 中新建一个文件夹，例如“图像提示词”，然后在本 App 中选择该文件夹。")

        result_box.insert(tk.END, "\n".join(lines))
        result_box.config(state="disabled")

        if obsidian_path:
            tk.Button(
                button_frame,
                text="打开 Obsidian",
                command=lambda: subprocess.Popen(["open", obsidian_path])
            ).pack(side="left", padx=(0, 8))
        else:
            tk.Button(
                button_frame,
                text="下载 Obsidian",
                command=lambda: webbrowser.open("https://obsidian.md/download")
            ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="选择 Obsidian 保存目录",
            command=self.choose_output_dir
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="重新检查",
            command=lambda: [checker_window.destroy(), self.open_obsidian_status_checker()]
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="关闭",
            command=checker_window.destroy
        ).pack(side="right")


    def open_model_advisor(self):
        advisor_window = tk.Toplevel(self.root)
        advisor_window.title("Gemma 模型推荐器")
        advisor_window.geometry("720x560")

        status_var = tk.StringVar(value="正在检测设备和本地模型...")
        tk.Label(advisor_window, textvariable=status_var, anchor="w").pack(fill="x", padx=10, pady=(10, 6))

        result_box = scrolledtext.ScrolledText(advisor_window, wrap="word")
        result_box.pack(fill="both", expand=True, padx=10, pady=6)

        button_frame = tk.Frame(advisor_window)
        button_frame.pack(fill="x", padx=10, pady=(4, 10))

        state = {
            "recommended_model": None
        }

        def set_text(content):
            result_box.delete("1.0", tk.END)
            result_box.insert(tk.END, content)

        def use_recommended_model():
            model = state.get("recommended_model")
            if not model:
                messagebox.showwarning("暂无推荐", "还没有可用的推荐模型。")
                return

            self.model_var.set(model)
            self.save_current_config()
            self.refresh_environment()
            status_var.set(f"已使用推荐模型：{model}")

        def download_recommended_model():
            model = state.get("recommended_model")
            if not model:
                messagebox.showwarning("暂无推荐", "还没有可用的推荐模型。")
                return

            self.model_var.set(model)
            self.save_current_config()
            advisor_window.destroy()
            self.pull_gemma_model()

        tk.Button(button_frame, text="使用推荐模型", command=use_recommended_model).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="下载推荐模型", command=download_recommended_model).pack(side="left", padx=(0, 8))
        tk.Button(button_frame, text="关闭", command=advisor_window.destroy).pack(side="right")

        def worker():
            try:
                hardware = hardware_check.get_hardware_profile()

                env_result = env_check.check_environment(self.model_var.get().strip() or DEFAULT_MODEL_NAME)
                installed_models = env_result.get("models", [])

                advice = model_advisor.recommend_gemma_models(hardware, installed_models)
                state["recommended_model"] = advice["recommended"]

                content = model_advisor.format_advice_text(hardware, advice)

                self.root.after(0, lambda: status_var.set("检测完成"))
                self.root.after(0, lambda: set_text(content))

            except Exception as e:
                log_error(f"模型推荐失败：{e}")
                self.root.after(0, lambda: status_var.set("模型推荐失败"))
                self.root.after(0, lambda: set_text(str(e)))

        threading.Thread(target=worker, daemon=True).start()


    def pull_gemma_model(self):
        model_name = self.model_var.get().strip() or DEFAULT_MODEL_NAME

        confirmed = messagebox.askyesno(
            "下载模型",
            f"将通过 Ollama 下载模型：{model_name}\n\n模型文件较大，可能需要较长时间，并占用数 GB 磁盘空间。\n\n是否开始下载？"
        )

        if not confirmed:
            return

        def worker():
            try:
                self.set_status(f"正在下载 {model_name}...")
                self.set_env_status(f"正在下载 {model_name}...\n请保持网络连接，不要关闭 App。")

                ok, msg = env_check.start_ollama_service()
                if not ok:
                    raise RuntimeError(msg)

                def progress(message):
                    self.set_env_status(f"正在下载 {model_name}...\n{message}")
                    self.set_status(message)

                success = env_check.pull_model(model_name, progress_callback=progress)

                if success:
                    self.set_status("模型下载完成。")
                    self.refresh_environment()
                else:
                    self.set_status("模型下载未完成。")
                    messagebox.showwarning("下载未完成", "模型下载未完成，请稍后重试。")

            except Exception as e:
                log_error(f"下载模型失败：{e}")
                self.set_status("模型下载失败")
                messagebox.showerror("模型下载失败", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def generate(self):
        user_idea = self.idea_text.get("1.0", tk.END).strip()
        output_dir = self.output_dir_var.get().strip()

        if not user_idea:
            messagebox.showwarning("缺少输入", "请先输入画面想法。")
            return

        model_name = self.model_var.get().strip() or DEFAULT_MODEL_NAME
        env_result = env_check.check_environment(model_name)

        if not env_result["ollama_installed"]:
            messagebox.showwarning(
                "缺少 Ollama",
                "未检测到 Ollama。请先安装 Ollama，然后点击“刷新自检”。"
            )
            return

        if not env_result["ollama_service_running"]:
            messagebox.showwarning(
                "Ollama 未运行",
                "Ollama 服务未运行。请点击“启动 Ollama”，然后再生成。"
            )
            return

        if not env_result["model_installed"]:
            messagebox.showwarning(
                "缺少模型",
                f"未检测到模型 {model_name}。请点击“推荐 Gemma 模型”，选择并下载合适的模型。"
            )
            return

        self.save_current_config()

        self.generate_button.config(state="disabled")
        self.status_var.set("准备生成...")

        thread = threading.Thread(
            target=self.generate_worker,
            args=(user_idea,),
            daemon=True
        )
        thread.start()

    def generate_worker(self, user_idea):
        try:
            model_name = self.model_var.get().strip() or DEFAULT_MODEL_NAME
            output_dir = self.output_dir_var.get().strip()
            count = int(self.count_var.get())
            count = max(3, min(5, count))
            style_hint = self.style_var.get().strip() or "高质量、画面干净、构图明确、有商业完成度"
            platform_hint = self.platform_var.get().strip() or "通用生图工具"

            ensure_ollama_running(self.set_status)

            prompts = call_gemma(
                model_name=model_name,
                user_idea=user_idea,
                count=count,
                style_hint=style_hint,
                platform_hint=platform_hint,
                status_callback=self.set_status
            )

            markdown = build_markdown(user_idea, style_hint, platform_hint, prompts)

            self.set_result(markdown)

            if output_dir:
                file_path = save_to_obsidian(output_dir, user_idea, markdown)
                self.set_status(f"已保存：{file_path}")
            else:
                warning = (
                    "未设置 Markdown 保存目录。本次结果只显示在窗口中，"
                    "不会自动保存为文件。请尽快复制生成结果。"
                )
                self.set_status("未设置保存目录，请尽快复制生成结果。")
                self.root.after(0, lambda: messagebox.showwarning("未设置保存目录", warning))

        except Exception as e:
            log_error(f"生成失败：{e}")
            self.set_status("生成失败")
            messagebox.showerror("生成失败", str(e))

        finally:
            self.root.after(0, lambda: self.generate_button.config(state="normal"))


def main():
    root = tk.Tk()
    PromptWriterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
