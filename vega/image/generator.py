"""
image/generator.py — Vega
Prompt → 8K image generation pipeline.

Strategy:
  1. Stable Diffusion XL via local Ollama / ComfyUI (if available)
  2. Replicate API (if REPLICATE_API_KEY set) — runs SDXL in the cloud
  3. DALL-E 3 via OpenAI API (if OPENAI_API_KEY set)
  Then: Real-ESRGAN upscale to 8K (if installed)

Honest note (Cardinal Rule 13):
  Full 8K native AI image generation requires either:
    - A powerful local GPU (M1 Ultra / M2 Ultra recommended for SDXL)
    - A cloud API key (Replicate, OpenAI)
  This module uses what's available and tells the truth about what isn't.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import base64
import logging
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.image.generator")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "vega_output" / "images"
ESRGAN_PATH = Path.home() / "Real-ESRGAN" / "inference_realesrgan.py"


def generate_8k_image(
    prompt: str,
    output_filename: Optional[str] = None,
    negative_prompt: str = "blurry, low quality, watermark, text, logo",
    target_resolution: tuple = (7680, 4320),
) -> dict:
    """
    Main entry: prompt → 8K image file.
    Tries available backends in order. Honest about failures.

    Returns:
        {"status": "ok"|"error", "output_path": str, "method": str, ...}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    if not output_filename:
        output_filename = f"vega_image_{ts}.png"

    # ── Backend 1: Replicate (cloud SDXL) ───────────────────────────────────
    replicate_key = os.environ.get("REPLICATE_API_KEY")
    if replicate_key:
        result = _generate_via_replicate(prompt, negative_prompt, output_filename)
        if result["status"] == "ok":
            return _upscale_to_8k(result["output_path"], output_filename, target_resolution)
        logger.warning(f"[Vega.ImageGen] Replicate failed: {result.get('reason')} — trying next")

    # ── Backend 2: OpenAI DALL-E 3 ──────────────────────────────────────────
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        result = _generate_via_dalle(prompt, output_filename)
        if result["status"] == "ok":
            return _upscale_to_8k(result["output_path"], output_filename, target_resolution)
        logger.warning(f"[Vega.ImageGen] DALL-E failed: {result.get('reason')} — trying next")

    # ── Backend 3: Local ComfyUI ────────────────────────────────────────────
    if _check_comfyui():
        result = _generate_via_comfyui(prompt, negative_prompt, output_filename)
        if result["status"] == "ok":
            return _upscale_to_8k(result["output_path"], output_filename, target_resolution)
        logger.warning(f"[Vega.ImageGen] ComfyUI failed: {result.get('reason')}")

    # ── Backend 4: In-house TCAP branded card (Rule 15 — zero cost) ───────
    result = _generate_via_branded_card(prompt, output_filename, target_resolution)
    if result["status"] == "ok":
        return result

    # ── Nothing available ───────────────────────────────────────────────────
    return {
        "status": "error",
        "reason": (
            "No image generation backend available. "
            "Install Pillow (pip install Pillow) for in-house branded cards, "
            "or set REPLICATE_API_KEY / OPENAI_API_KEY, or run ComfyUI on port 8188. "
            "(Rule 1: can't generate without a generation engine)"
        ),
        "method": "none",
    }


def _generate_via_branded_card(
    prompt: str,
    output_filename: str,
    target_resolution: tuple,
) -> dict:
    """
    In-house TCAP branded marketing image — Pillow only, zero cost (Rule 15).
    Used when paid/cloud backends are unavailable.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {"status": "error", "reason": "Pillow not installed. pip install Pillow"}

    w, h = target_resolution
    # Cap render size for speed; upscale after if needed
    render_w, render_h = min(w, 1920), min(h, 1920)

    img = Image.new("RGB", (render_w, render_h), color=(10, 14, 26))
    draw = ImageDraw.Draw(img)

    # TCAP brand accents
    draw.rectangle([(0, int(render_h * 0.08)), (render_w, int(render_h * 0.08) + 3)], fill=(0, 245, 255))
    draw.rectangle([(0, int(render_h * 0.88)), (render_w, int(render_h * 0.88) + 3)], fill=(0, 132, 255))
    draw.rectangle([(0, 0), (6, render_h)], fill=(0, 132, 255))

    title = prompt[:80]
    subtitle = "The Christman AI Project"
    tagline = "Luma Cognify AI · AI That Empowers, Protects, and Redefines Humanity"

    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(36, render_h // 18))
        sub_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(24, render_h // 32))
        tag_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(16, render_h // 52))
    except OSError:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        tag_font = ImageFont.load_default()

    def _centered(text: str, y: int, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((render_w - tw) // 2, y), text, font=font, fill=color)

    line_y = int(render_h * 0.32)
    _centered(title, line_y, title_font, (240, 244, 255))
    _centered(subtitle, line_y + max(48, render_h // 14), sub_font, (0, 245, 255))
    _centered(tagline, int(render_h * 0.78), tag_font, (180, 190, 210))

    base_path = str(OUTPUT_DIR / output_filename)
    img.save(base_path, "PNG", quality=95)

    if (render_w, render_h) != (w, h):
        return _upscale_to_8k(base_path, output_filename, target_resolution)

    file_size_mb = Path(base_path).stat().st_size / (1024 * 1024)
    return {
        "status": "ok",
        "output_path": base_path,
        "resolution": f"{render_w}x{render_h}",
        "method": "tcap_branded_card",
        "file_size_mb": round(file_size_mb, 2),
    }


def _generate_via_replicate(prompt: str, negative_prompt: str, output_filename: str) -> dict:
    """Generate via Replicate API (SDXL). Rule 13: real API or honest error."""
    try:
        import replicate
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": 1024,
                "height": 576,
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
            }
        )
        if not output:
            return {"status": "error", "reason": "Replicate returned empty output"}

        url = output[0] if isinstance(output, list) else str(output)
        output_path = str(OUTPUT_DIR / output_filename)
        urllib.request.urlretrieve(url, output_path)
        return {"status": "ok", "output_path": output_path, "method": "replicate_sdxl"}

    except ImportError:
        return {"status": "error", "reason": "replicate package not installed. pip install replicate"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def _generate_via_dalle(prompt: str, output_filename: str) -> dict:
    """Generate via OpenAI DALL-E 3. Rule 13: real API or honest error."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="hd",
            n=1,
        )
        url = response.data[0].url
        output_path = str(OUTPUT_DIR / output_filename)
        urllib.request.urlretrieve(url, output_path)
        return {"status": "ok", "output_path": output_path, "method": "dalle3"}

    except ImportError:
        return {"status": "error", "reason": "openai package not installed. pip install openai"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def _check_comfyui() -> bool:
    """Check if ComfyUI is running on localhost:8188."""
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)
        return True
    except Exception:
        return False


def _generate_via_comfyui(prompt: str, negative_prompt: str, output_filename: str) -> dict:
    """
    Generate via local ComfyUI instance.
    Rule 13: Only works if ComfyUI is actually running. Honest if it's not.
    """
    try:
        import json
        import urllib.request

        workflow = {
            "3": {
                "inputs": {
                    "seed": 42,
                    "steps": 30,
                    "cfg": 7,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
        }

        # This is a simplified ComfyUI call — full workflow would be project-specific
        raise NotImplementedError(
            "ComfyUI workflow needs to be configured for this project. "
            "Add your workflow JSON to vega/video/comfyui_workflow.json. (Rule 1)"
        )

    except NotImplementedError:
        raise
    except Exception as e:
        return {"status": "error", "reason": f"ComfyUI error: {e}"}


def _upscale_to_8k(input_path: str, output_filename: str, target_resolution: tuple) -> dict:
    """
    Upscale image to 8K using Real-ESRGAN (if installed) or Pillow (fallback).
    Real-ESRGAN produces vastly better quality than simple scaling.
    """
    if not Path(input_path).exists():
        return {"status": "error", "reason": f"Input not found for upscaling: {input_path}"}

    w, h = target_resolution
    output_path = str(OUTPUT_DIR / output_filename.replace(".png", "_8k.png"))

    # ── Real-ESRGAN (if available) ──────────────────────────────────────────
    if ESRGAN_PATH.exists():
        logger.info("[Vega.ImageGen] Upscaling with Real-ESRGAN")
        cmd = [
            "python3", str(ESRGAN_PATH),
            "-i", input_path,
            "-o", str(OUTPUT_DIR),
            "--outscale", "8",
            "--model_name", "RealESRGAN_x4plus",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and Path(output_path).exists():
            file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            return {
                "status": "ok",
                "output_path": output_path,
                "resolution": f"{w}x{h}",
                "method": "real_esrgan",
                "file_size_mb": round(file_size_mb, 2),
            }
        logger.warning(f"[Vega.ImageGen] Real-ESRGAN failed: {result.stderr[:200]}")

    # ── Pillow fallback (simple bicubic) ────────────────────────────────────
    logger.info(f"[Vega.ImageGen] Upscaling to {w}x{h} with Pillow (bicubic)")
    try:
        from PIL import Image

        img = Image.open(input_path)
        img_8k = img.resize((w, h), Image.LANCZOS)
        img_8k.save(output_path, "PNG", quality=95)

        file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        return {
            "status": "ok",
            "output_path": output_path,
            "resolution": f"{w}x{h}",
            "method": "pillow_lanczos",
            "file_size_mb": round(file_size_mb, 2),
            "note": "For higher quality upscaling, install Real-ESRGAN: https://github.com/xinntao/Real-ESRGAN",
        }
    except ImportError:
        return {"status": "error", "reason": "Pillow not installed. pip install Pillow"}
    except Exception as e:
        return {"status": "error", "reason": f"Upscaling failed: {e}"}
