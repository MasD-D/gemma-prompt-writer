# Gemma Prompt Writer

English | 中文

A local-first macOS app for turning rough image ideas into structured image-generation prompts.

一个本地优先的 macOS 应用，用于把粗略的画面想法转换成结构化生图提示词。

---

## Overview / 项目简介

Gemma Prompt Writer connects to your local Ollama service, uses a local Gemma model to generate prompt variants, and saves the result as Markdown files into an Obsidian folder.

Gemma Prompt Writer 会连接你电脑本地的 Ollama 服务，调用本地 Gemma 模型生成多段生图提示词，并将结果保存为 Markdown 文件到你选择的 Obsidian 文件夹中。

This project is designed for people who want a simple local prompt-writing tool without sending their raw ideas to a remote prompt-generation service.

本项目适合需要本地化提示词生成工具的用户，尤其是希望把画面想法沉淀到 Obsidian 中进行长期管理的人。

---

## What it does / 它能做什么

Gemma Prompt Writer helps you turn a simple visual idea into reusable image-generation prompts.

Gemma Prompt Writer 可以把一句简单的画面想法扩展成可复用的生图提示词。

It generates:

它会生成：

- English prompt
- 中文提示词
- Negative prompt
- Usage note
- Obsidian-friendly Markdown output

对应中文：

- 英文生图提示词
- 中文生图提示词
- 负向提示词
- 使用建议
- 适合 Obsidian 管理的 Markdown 文件

Typical use cases:

典型使用场景：

- Midjourney / GPT Image / Stable Diffusion prompt drafting
- Xiaohongshu cover ideas
- App Store creative exploration
- Poster and visual concept ideation
- Personal prompt library management in Obsidian

对应中文：

- Midjourney / GPT Image / Stable Diffusion 提示词草稿
- 小红书封面创意
- App Store 视觉探索
- 海报与视觉概念构思
- 在 Obsidian 中管理个人提示词库

---

## Key features / 核心功能

- Local-first prompt generation  
  本地优先的提示词生成

- Connects to local Ollama API  
  连接本机 Ollama API

- Default model: gemma4:12b  
  默认模型：gemma4:12b

- Generates 3–5 prompt variants  
  支持生成 3–5 段提示词变体

- Saves generated prompts as Markdown  
  将生成结果保存为 Markdown 文件

- Obsidian-friendly output  
  输出格式适合 Obsidian 管理

- Environment check panel  
  内置环境自检面板

- Detects Ollama installation status  
  检测 Ollama 是否已安装

- Detects Ollama service status  
  检测 Ollama 服务是否正在运行

- Detects whether the target model is installed  
  检测目标模型是否已安装

- Can pull the target model through Ollama after user confirmation  
  用户确认后，可以通过 Ollama 拉取目标模型

- macOS GUI built with Tkinter  
  使用 Tkinter 构建 macOS 图形界面

- Styled DMG installer  
  提供带安装引导的 DMG 安装包

---

## Quick start / 快速开始

### 1. Install Ollama / 安装 Ollama

Download and install Ollama from the official website.

请先从 Ollama 官网下载并安装 Ollama。

    https://ollama.com/download

### 2. Download Gemma Prompt Writer / 下载 Gemma Prompt Writer

Go to the Releases page and download the latest DMG.

进入 Releases 页面，下载最新版本的 DMG 安装包。

    https://github.com/MasD-D/gemma-prompt-writer/releases

### 3. Install the app / 安装应用

Open the DMG and drag the app into Applications.

打开 DMG 后，将 App 拖入 Applications 文件夹。

### 4. Launch the app / 启动应用

Open Gemma Prompt Writer from Applications.

从 Applications 文件夹中打开 Gemma Prompt Writer。

On first launch, check the Environment panel. The app will show:

首次启动后，请查看顶部的环境自检区域。App 会显示：

- Whether Ollama is installed  
  Ollama 是否已安装

- Whether Ollama service is running  
  Ollama 服务是否正在运行

- Whether gemma4:12b is installed  
  gemma4:12b 是否已安装

If gemma4:12b is missing, click "Download Gemma4 12B" inside the app.

如果缺少 gemma4:12b，可以点击 App 内的「下载 Gemma4 12B」。

### 5. Generate prompts / 生成提示词

Choose an Obsidian output folder, enter your image idea, and click the generate button.

选择 Obsidian 输出目录，输入你的画面想法，然后点击生成按钮。

The app will create a Markdown file in your selected folder.

App 会在你选择的目录中创建一个 Markdown 文件。

---

## Requirements / 使用要求

For end users:

普通用户需要：

- macOS
- Ollama
- gemma4:12b or another Ollama-compatible text model
- Optional: Obsidian

对应中文：

- macOS
- Ollama
- gemma4:12b 或其他兼容 Ollama 的文本模型
- 可选：Obsidian

For developers:

开发者需要：

- Python 3.14 or compatible Python 3 version
- Tkinter support
- requests
- PyInstaller
- Pillow
- create-dmg

对应中文：

- Python 3.14 或兼容的 Python 3 版本
- Tkinter 支持
- requests
- PyInstaller
- Pillow
- create-dmg

If you use Homebrew Python and Tkinter is missing, install Tkinter support:

如果你使用 Homebrew Python，并且缺少 Tkinter，可以安装 Tkinter 支持：

    brew install python-tk@3.14

Install dependencies:

安装依赖：

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

Install packaging tool:

安装 DMG 打包工具：

    brew install create-dmg

---

## Run from source / 从源码运行

Run the app directly from source:

直接从源码运行 App：

    python3 prompt_writer_gui.py

---

## Build DMG / 构建 DMG

Build a styled macOS DMG installer:

构建带安装引导的 macOS DMG 安装包：

    ./build_release.sh

The generated DMG will be placed in the project root.

生成的 DMG 文件会出现在项目根目录。

---

## How it works / 工作原理

The app talks to the local Ollama API:

App 会调用本地 Ollama API：

    http://localhost:11434/api

Main flow:

主要流程：

    User idea
      ↓
    Local Gemma model via Ollama
      ↓
    Structured prompt output
      ↓
    Markdown export
      ↓
    Obsidian folder

对应中文：

    用户输入画面想法
      ↓
    通过 Ollama 调用本地 Gemma 模型
      ↓
    生成结构化提示词
      ↓
    导出 Markdown 文件
      ↓
    保存到 Obsidian 文件夹

---

## Project structure / 项目结构

    prompt_image_pipeline/
      prompt_writer_gui.py      # Main GUI app / 主图形界面程序
      env_check.py              # Environment checks / Ollama 与模型环境检测
      build_release.sh          # macOS DMG build script / macOS DMG 构建脚本
      requirements.txt          # Runtime dependencies / 运行依赖
      requirements-dev.txt      # Build dependencies / 构建依赖
      README.md
      LICENSE
      .gitignore

---

## FAQ / 常见问题

### Does this app include Gemma model weights? / 这个 App 是否包含 Gemma 模型权重？

No. This project does not include Gemma model weights.

不包含。本项目不内置 Gemma 模型权重。

The app connects to Ollama on your machine. If the target model is missing, the app can ask Ollama to pull it after user confirmation.

App 会连接你电脑本机的 Ollama。如果目标模型缺失，App 可以在用户确认后通过 Ollama 拉取模型。

### Does this app upload my prompts? / 这个 App 会上传我的提示词吗？

No server-side upload is implemented in this project.

本项目没有实现服务端上传逻辑。

Prompt generation happens through the local Ollama API.

提示词生成通过本机 Ollama API 完成。

### Why do I need Ollama? / 为什么需要 Ollama？

Ollama provides the local model runtime and local API used by this app.

Ollama 提供本地模型运行环境和本地 API，本 App 依赖它调用本地模型。

### Can I use another model? / 可以使用其他模型吗？

Yes. You can edit the model name field in the app, as long as the model is available in Ollama.

可以。只要模型已经在 Ollama 中可用，你可以在 App 中修改模型名称。

### Why does macOS warn that the developer cannot be verified? / 为什么 macOS 提示无法验证开发者？

Current public DMG builds are not notarized.

当前公开 DMG 构建版本尚未进行 Apple notarization 公证。

For now, use right-click → Open if macOS blocks the first launch.

如果首次启动被 macOS 拦截，可以使用右键 App → 打开。

---

## Roadmap / 路线图

Planned improvements:

后续计划：

- Better app icon  
  更好的 App 图标

- More prompt templates  
  更多提示词模板

- Prompt history browser  
  提示词历史浏览器

- One-click copy buttons  
  一键复制按钮

- Model selection dropdown  
  模型选择下拉框

- Improved error log viewer  
  更好的错误日志查看器

- GitHub Actions release build  
  GitHub Actions 自动构建 Release

- Signed and notarized macOS release  
  签名并公证的 macOS 发布版本

---

## License / 许可证

MIT
