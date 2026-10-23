#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
帧刻服务 · 模型生图 调用示例（可直接运行）
=========================================

用法：
  python vidshell_image_gen.py --vk <你的vk令牌> --prompt "一句话"
  python vidshell_image_gen.py --vk <你的vk令牌> --prompt "..." --size 1024x768 --out ./img

说明：
- 网关为 OpenAI 兼容：base_url = https://aytrim.top/vidshell/v1
- 鉴权：Authorization: Bearer vk_xxx（vk 令牌从 GET /vidshell/api/ai/token 领取，或用桌面 dispatch 通道）
- 客户端传的 model 会被服务端忽略，真实模型由数据库选池决定；响应 model 会被改写成公开名 vidshell-images-1.0
- 敏感令牌请通过环境变量 VIDSHELL_VK 注入，不要写死进文件/版本库：
      export VIDSHELL_VK="vk_..."      # Windows PowerShell: $env:VIDSHELL_VK="vk_..."

依赖：仅需 httpx（或 curl，无需额外安装）。
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:  # 允许纯 curl 环境：给出提示后退出
    print("未安装 httpx，请先 pip install httpx（或用 curl 直接调用）。", file=sys.stderr)
    raise

BASE = "https://aytrim.top/vidshell"
GENERATE_URL = f"{BASE}/v1/images/generations"
# 与网关 AI_IMAGE_TIMEOUT_SEC 默认 180s 对齐；连接超时单独 15s
CONNECT_TIMEOUT = 15.0
READ_TIMEOUT = 180.0


def _resolve_vk(explicit: str) -> str:
    """优先取命令行 --vk，其次环境变量 VIDSHELL_VK；都没有则报用法。"""
    tok = (explicit or os.environ.get("VIDSHELL_VK", "")).strip()
    if not tok:
        print("错误：未提供 vk 令牌。", file=sys.stderr)
        print("  方式 1：python vidshell_image_gen.py --vk vk_xxx ...", file=sys.stderr)
        print("  方式 2：export VIDSHELL_VK=vk_xxx 后省略 --vk", file=sys.stderr)
        sys.exit(2)
    return tok


def generate(vk: str, prompt: str, size: str = "1024x1024") -> dict:
    """调生图端点，返回原始响应 json（含 data[].url / data[].b64_json）。"""
    payload = {
        "model": "vidshell-images-1.0",   # 会被忽略，可写任意值
        "prompt": prompt,
        "n": 1,                            # 当前仅支持 n=1
        "size": size,
    }
    with httpx.Client(timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
        resp = client.post(
            GENERATE_URL,
            headers={"Authorization": f"Bearer {vk}"},
            json=payload,
        )
    if resp.status_code >= 400:
        print(f"[HTTP {resp.status_code}] 生图失败：\n{resp.text[:1000]}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def save_result(data: dict, out_dir: str, prefix: str = "vidshell_image") -> Path:
    """把返回体里的图片落到本地（优先 url 下载，其次 b64_json 解码）。"""
    item = (data.get("data") or [{}])[0]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if item.get("b64_json"):
        p = out_path / f"{prefix}_{stamp}.png"
        p.write_bytes(base64.b64decode(item["b64_json"]))
        return p
    if item.get("url"):
        p = out_path / f"{prefix}_{stamp}.png"
        with httpx.Client(timeout=READ_TIMEOUT, follow_redirects=True) as client:
            img = client.get(item["url"]).content
        p.write_bytes(img)
        return p
    raise RuntimeError("响应里既无 b64_json 也无 url，无法保存图片：\n" + str(data)[:500])


def main() -> None:
    ap = argparse.ArgumentParser(description="帧刻服务模型生图调用示例")
    ap.add_argument("--vk", default="", help="vk 网关令牌（或设环境变量 VIDSHELL_VK）")
    ap.add_argument("--prompt", required=True, help="生图提示词")
    ap.add_argument("--size", default="1024x1024", help="尺寸，默认 1024x1024")
    ap.add_argument("--out", default="./vidshell_images", help="图片保存目录")
    ap.add_argument("--prefix", default="vidshell_image", help="输出文件名前缀（默认 vidshell_image）")
    ap.add_argument("--json", action="store_true", help="打印完整响应 JSON（默认只打印图片路径）")
    args = ap.parse_args()

    vk = _resolve_vk(args.vk)
    print(f"-> POST {GENERATE_URL}  size={args.size}")
    data = generate(vk, args.prompt, args.size)
    if args.json:
        print(_pretty(data))
    p = save_result(data, args.out, prefix=args.prefix)
    print(f"[OK] 已保存：{p.resolve()}")


def _pretty(d) -> str:
    import json
    return json.dumps(d, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
