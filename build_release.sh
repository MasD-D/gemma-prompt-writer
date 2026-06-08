#!/bin/bash
set -e

APP_NAME="Gemma Prompt Writer"
VERSION="0.3.5"
BUILD_NAME="${APP_NAME} v${VERSION}"
RELEASE_DIR="release"
ASSETS_DIR="assets"
DMG_NAME="${BUILD_NAME}.dmg"
BACKGROUND_PNG="${ASSETS_DIR}/dmg-background.png"

echo "==> Cleaning old build folders..."

pkill -f "$APP_NAME" 2>/dev/null || true

hdiutil detach "/Volumes/Gemma Prompt Writer v0.3.0" -force 2>/dev/null || true
hdiutil detach "/Volumes/Gemma Prompt Writer v0.3.1" -force 2>/dev/null || true
hdiutil detach "/Volumes/Gemma Prompt Writer v0.3.2" -force 2>/dev/null || true

chmod -R u+w build dist "$RELEASE_DIR" 2>/dev/null || true
chflags -R nouchg build dist "$RELEASE_DIR" 2>/dev/null || true

rm -rf build 2>/dev/null || true
rm -rf "$RELEASE_DIR" 2>/dev/null || true

if [ -d "dist" ]; then
  rm -rf dist 2>/dev/null || mv dist "dist_old_$(date +%Y%m%d_%H%M%S)"
fi

rm -f "${BUILD_NAME}.spec" 2>/dev/null || true
rm -f "$DMG_NAME" 2>/dev/null || true

echo "==> Building app with PyInstaller..."

pyinstaller \
  --windowed \
  --name "$BUILD_NAME" \
  --icon "$ASSETS_DIR/app_icon.icns" \
  --add-data "$ASSETS_DIR/app_icon_256.png:assets" \
  prompt_writer_gui.py

echo "==> Preparing release folder..."

mkdir -p "$RELEASE_DIR"
mkdir -p "$ASSETS_DIR"

cp -R "dist/${BUILD_NAME}.app" "$RELEASE_DIR/"

cat > "$RELEASE_DIR/使用说明.md" <<'EOF'
# Gemma Prompt Writer 使用说明

## 这个 App 是什么

这是一个本地生图提示词生成器。

它会连接你电脑本地的 Ollama 和 Gemma 模型，根据你输入的画面想法，生成 3～5 段生图提示词，并自动保存到你选择的 Obsidian 文件夹。

## 使用前需要什么

你需要先安装 Ollama。

如果还没有安装 Ollama，请打开：

https://ollama.com/download

App 会自动检测：
- Ollama 是否安装
- Ollama 服务是否运行
- gemma4:12b 模型是否安装

如果缺少 gemma4:12b，可以在 App 里点击「下载 Gemma4 12B」。

## 第一次使用

1. 打开 App
2. 查看顶部「环境自检」
3. 选择 Obsidian 保存目录
4. 输入画面想法
5. 点击「生成提示词并保存到 Obsidian」

## 推荐安装方式

打开 DMG 后，把 Gemma Prompt Writer 拖到 Applications 文件夹。

## 常见问题

### 点击生成没有反应

请先看顶部环境自检是否全部正常。

如果仍然失败，可以查看日志：

~/Library/Application Support/Gemma Prompt Writer/app.log

### macOS 提示无法验证开发者

这是未签名内测版的正常现象。

可以右键 App，选择「打开」，再确认打开。
EOF

echo "==> Creating DMG background..."

python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 760, 420
out = Path("assets/dmg-background.png")
out.parent.mkdir(parents=True, exist_ok=True)

img = Image.new("RGB", (W, H), (247, 248, 250))
draw = ImageDraw.Draw(img)

def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

title_font = font(28, True)
body_font = font(16)
small_font = font(13)

# Card background
draw.rounded_rectangle(
    [34, 34, W - 34, H - 34],
    radius=28,
    fill=(255, 255, 255),
    outline=(228, 232, 238),
    width=1,
)

# Title
draw.text((70, 62), "Gemma Prompt Writer", fill=(35, 42, 55), font=title_font)
draw.text((70, 100), "Drag the app to Applications to install", fill=(90, 98, 112), font=body_font)

# Icon landing zones
draw.rounded_rectangle([118, 176, 282, 312], radius=22, fill=(249, 250, 252), outline=(230, 233, 238))
draw.rounded_rectangle([478, 176, 642, 312], radius=22, fill=(249, 250, 252), outline=(230, 233, 238))

# Arrow
y = 244
draw.line([315, y, 445, y], fill=(120, 128, 142), width=5)
draw.polygon([(445, y), (420, y - 16), (420, y + 16)], fill=(120, 128, 142))

# Captions
draw.text((149, 324), "App", fill=(92, 100, 114), font=small_font)
draw.text((512, 324), "Applications", fill=(92, 100, 114), font=small_font)

# Footer
draw.text((70, 365), "Local Gemma-powered image prompt generator", fill=(135, 142, 154), font=small_font)

img.save(out)
print(f"Saved {out}")
PY

echo "==> Creating styled DMG..."

create-dmg \
  --volname "$BUILD_NAME" \
  --background "$BACKGROUND_PNG" \
  --window-pos 200 120 \
  --window-size 760 420 \
  --text-size 13 \
  --icon-size 96 \
  --icon "$BUILD_NAME.app" 200 245 \
  --icon "使用说明.md" 380 88 \
  --app-drop-link 560 245 \
  --hide-extension "$BUILD_NAME.app" \
  "$DMG_NAME" \
  "$RELEASE_DIR"

echo "==> Done."
echo "App: dist/${BUILD_NAME}.app"
echo "DMG: ${DMG_NAME}"
