GEMMA_MODELS = {
    "gemma3:4b": {
        "estimated_size_gb": 4,
        "label": "低配兜底",
        "description": "适合 8GB 内存或希望响应更快的设备。",
    },
    "gemma3:12b": {
        "estimated_size_gb": 9,
        "label": "稳妥中档",
        "description": "适合中等配置设备，质量和资源占用相对平衡。",
    },
    "gemma4:e2b": {
        "estimated_size_gb": 8,
        "label": "推荐默认",
        "description": "适合普通本地提示词生成，资源占用相对可控。",
    },
    "gemma4:e4b": {
        "estimated_size_gb": 11,
        "label": "增强默认",
        "description": "适合 16GB 以上设备，提示词质量通常更好。",
    },
    "gemma4:12b": {
        "estimated_size_gb": 9,
        "label": "高质量推荐",
        "description": "适合 16GB 到 24GB 以上设备，适合更细腻的提示词扩写。",
    },
    "gemma4:26b": {
        "estimated_size_gb": 22,
        "label": "高配模型",
        "description": "适合 32GB 以上设备，下载和运行成本更高。",
    },
    "gemma4:31b": {
        "estimated_size_gb": 25,
        "label": "高配上限",
        "description": "适合 64GB 左右或更高配置设备。",
    },
}


def filter_installed_gemma_models(installed_models):
    return sorted([m for m in installed_models if m.startswith("gemma")])


def _base_recommendation_by_ram(ram_gb):
    if ram_gb <= 8:
        return "gemma3:4b", "gemma4:e2b", "gemma3:4b"
    if ram_gb <= 16:
        return "gemma4:e2b", "gemma4:12b", "gemma3:4b"
    if ram_gb <= 24:
        return "gemma4:12b", "gemma4:e4b", "gemma4:e2b"
    if ram_gb <= 48:
        return "gemma4:26b", "gemma4:12b", "gemma4:e2b"
    return "gemma4:31b", "gemma4:26b", "gemma4:12b"


def _downgrade_for_disk(model_name, available_disk_gb):
    # 保留 10GB 缓冲，避免把用户磁盘空间吃得太紧。
    ordered = [
        "gemma4:31b",
        "gemma4:26b",
        "gemma4:12b",
        "gemma4:e4b",
        "gemma4:e2b",
        "gemma3:12b",
        "gemma3:4b",
    ]

    if model_name not in ordered:
        return model_name, False

    start = ordered.index(model_name)

    for candidate in ordered[start:]:
        need = GEMMA_MODELS[candidate]["estimated_size_gb"] + 10
        if available_disk_gb >= need:
            return candidate, candidate != model_name

    return "gemma3:4b", model_name != "gemma3:4b"


def recommend_gemma_models(hardware_profile, installed_models):
    ram = float(hardware_profile.get("total_memory_gb", 0) or 0)
    disk = float(hardware_profile.get("available_disk_gb", 0) or 0)
    installed_gemma = filter_installed_gemma_models(installed_models)

    recommended, quality, fallback = _base_recommendation_by_ram(ram)
    recommended_after_disk, downgraded = _downgrade_for_disk(recommended, disk)

    reason_parts = []

    if ram <= 8:
        reason_parts.append("检测到内存较小，优先推荐轻量 Gemma 模型。")
    elif ram <= 16:
        reason_parts.append("检测到 16GB 级别内存，推荐资源占用更可控的 Gemma 4 小模型。")
    elif ram <= 24:
        reason_parts.append("检测到 24GB 级别内存，推荐 gemma4:12b 作为质量和速度的平衡点。")
    elif ram <= 48:
        reason_parts.append("检测到较高内存，可以尝试更大的 Gemma 模型。")
    else:
        reason_parts.append("检测到高内存设备，可以尝试 Gemma 系列更大模型。")

    if downgraded:
        reason_parts.append("由于可用磁盘空间不足，已自动降级推荐模型。")

    if recommended_after_disk in installed_gemma:
        reason_parts.append("推荐模型已经安装，可以直接使用。")
    else:
        reason_parts.append("推荐模型尚未安装，可以在 App 内下载。")

    return {
        "recommended": recommended_after_disk,
        "quality_option": quality,
        "fallback_option": fallback,
        "recommended_info": GEMMA_MODELS.get(recommended_after_disk, {}),
        "quality_info": GEMMA_MODELS.get(quality, {}),
        "fallback_info": GEMMA_MODELS.get(fallback, {}),
        "installed_gemma_models": installed_gemma,
        "is_recommended_installed": recommended_after_disk in installed_gemma,
        "reason": " ".join(reason_parts),
    }


def format_advice_text(hardware_profile, advice):
    lines = []

    lines.append("设备检测")
    lines.append("-" * 40)
    lines.append(f"macOS 版本：{hardware_profile.get('macos_version')}")
    lines.append(f"芯片架构：{hardware_profile.get('architecture')}")
    lines.append(f"Apple Silicon：{'是' if hardware_profile.get('is_apple_silicon') else '否'}")
    lines.append(f"CPU：{hardware_profile.get('cpu_brand')}")
    lines.append(f"内存：{hardware_profile.get('total_memory_gb')} GB")
    lines.append(f"可用磁盘空间：{hardware_profile.get('available_disk_gb')} GB")
    lines.append("")

    lines.append("Gemma 模型推荐")
    lines.append("-" * 40)
    lines.append(f"推荐模型：{advice['recommended']}")
    lines.append(f"推荐说明：{advice['recommended_info'].get('description', '')}")
    lines.append(f"是否已安装：{'是' if advice['is_recommended_installed'] else '否'}")
    lines.append("")
    lines.append(f"高质量选项：{advice['quality_option']}")
    lines.append(f"低配兜底：{advice['fallback_option']}")
    lines.append("")
    lines.append("本机已安装 Gemma 模型：")
    if advice["installed_gemma_models"]:
        for model in advice["installed_gemma_models"]:
            lines.append(f"- {model}")
    else:
        lines.append("- 暂未检测到 Gemma 系列模型")
    lines.append("")
    lines.append("推荐原因：")
    lines.append(advice["reason"])

    return "\n".join(lines)


if __name__ == "__main__":
    sample_hardware = {
        "total_memory_gb": 16,
        "available_disk_gb": 100,
        "architecture": "arm64",
        "is_apple_silicon": True,
        "cpu_brand": "Apple Silicon",
        "macos_version": "unknown",
    }
    print(recommend_gemma_models(sample_hardware, ["gemma4:12b"]))
