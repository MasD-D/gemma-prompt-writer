# Gemma Prompt Writer

A local macOS GUI app that uses Ollama + Gemma to generate image-generation prompts and save them as Markdown files into an Obsidian folder.

本项目是一个本地 macOS 图形界面工具。用户输入画面想法后，App 会调用本机 Ollama 中的 Gemma 模型，生成 3–5 段生图提示词，并保存为 Markdown 文件到用户选择的 Obsidian 目录。

## Features

- Local-first prompt generation
- Connects to local Ollama API
- Supports Gemma model, default: gemma4:12b
- Generates English prompt, Chinese prompt, negative prompt, and usage notes
- Saves generated prompts as Markdown
- Obsidian-friendly output
- Environment check panel
- Can detect Ollama, Ollama service status, and target model
- Can pull the target model through Ollama
- macOS GUI built with Tkinter
- Styled DMG build script included

## Requirements

For end users:

- macOS
- Ollama installed
- Recommended model: gemma4:12b
- Optional: Obsidian

For developers:

- Python 3.14 or compatible Python 3 version
- Tkinter support
- PyInstaller
- Pillow
- create-dmg

If you use Homebrew Python and Tkinter is missing, install Tkinter support:

    brew install python-tk@3.14

Install dependencies:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

Install packaging tool:

    brew install create-dmg

## Run from source

    python3 prompt_writer_gui.py

## Build DMG

    ./build_release.sh

The generated DMG will be placed in the project root.

## How it works

The app talks to the local Ollama API:

    http://localhost:11434/api

Main flow:

    User idea
      ↓
    Local Gemma model via Ollama
      ↓
    Structured prompt output
      ↓
    Markdown export
      ↓
    Obsidian folder

## Project structure

    prompt_image_pipeline/
      prompt_writer_gui.py      # Main GUI app
      env_check.py              # Ollama and model environment checks
      build_release.sh          # macOS DMG build script
      requirements.txt          # Runtime dependencies
      requirements-dev.txt      # Build dependencies
      README.md
      LICENSE
      .gitignore

## Notes

This project does not include Gemma model weights.

Users need to install Ollama separately. The app can detect and pull the target model through Ollama after user confirmation.

## License

MIT
