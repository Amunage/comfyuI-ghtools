import os
import asyncio
import shutil
import subprocess
import sys

import numpy as np
import torch
from PIL import Image, ImageOps
from aiohttp import web
import folder_paths

from nodes import PreviewImage
from server import PromptServer

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif",
}


def _find_latest_image(folder: str):
    """폴더 내에서 수정시간 기준 가장 최신 이미지 파일 경로를 반환한다."""
    return _find_image(folder, "time", "descending")


def _find_image(folder: str, sort_by: str = "time", sort_order: str = "descending"):
    """폴더 내에서 정렬 기준/순서에 따라 이미지 파일 경로를 반환한다."""
    entries = []
    for entry in os.scandir(folder):
        if not entry.is_file():
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        entries.append(entry)

    if not entries:
        return None

    reverse = (sort_order == "descending")
    if sort_by == "name":
        entries.sort(key=lambda e: e.name.lower(), reverse=reverse)
    else:  # time
        entries.sort(key=lambda e: e.stat().st_mtime, reverse=reverse)

    return entries[0].path


def _create_preview_image_info(image_path: str):
    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)

    filename_prefix = "ghtools_autoloader_preview"
    full_output_folder, filename, _, subfolder, _ = folder_paths.get_save_image_path(filename_prefix, temp_dir)
    os.makedirs(full_output_folder, exist_ok=True)

    ext = os.path.splitext(image_path)[1].lower() or ".png"
    counter = 1
    while True:
        preview_name = f"{filename}_{counter:05}{ext}"
        preview_path = os.path.join(full_output_folder, preview_name)
        if not os.path.exists(preview_path):
            break
        counter += 1

    shutil.copy2(image_path, preview_path)

    return {
        "filename": preview_name,
        "subfolder": subfolder,
        "type": "temp",
    }


def _open_folder_picker(initial_dir: str = ""):
    if sys.platform.startswith("win"):
        selected = _open_folder_picker_windows(initial_dir)
        if selected is not None:
            return selected

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError("tkinter is not available") from exc

    root = tk.Tk()
    root.withdraw()

    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    dialog_kwargs = {"mustexist": True}
    if initial_dir and os.path.isdir(initial_dir):
        dialog_kwargs["initialdir"] = initial_dir

    try:
        return filedialog.askdirectory(**dialog_kwargs)
    finally:
        root.destroy()


def _open_folder_picker_windows(initial_dir: str = ""):
    script = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class ForegroundHelper {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr hWnd);

    public static void ForceForeground(IntPtr hwnd) {
        IntPtr fg = GetForegroundWindow();
        uint fgPid;
        uint fgThread = GetWindowThreadProcessId(fg, out fgPid);
        uint curThread = GetCurrentThreadId();
        if (fgThread != curThread) {
            AttachThreadInput(curThread, fgThread, true);
            SetForegroundWindow(hwnd);
            BringWindowToTop(hwnd);
            AttachThreadInput(curThread, fgThread, false);
        } else {
            SetForegroundWindow(hwnd);
            BringWindowToTop(hwnd);
        }
    }
}
"@

$ownerForm = New-Object System.Windows.Forms.Form
$ownerForm.TopMost = $true
$ownerForm.StartPosition = 'Manual'
$ownerForm.Location = New-Object System.Drawing.Point(-32000, -32000)
$ownerForm.Size = New-Object System.Drawing.Size(1, 1)
$ownerForm.FormBorderStyle = 'None'
$ownerForm.ShowInTaskbar = $false
$ownerForm.Show()
$ownerForm.Activate()
[ForegroundHelper]::ForceForeground($ownerForm.Handle)

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Select image folder"
$dialog.ShowNewFolderButton = $true
$initialDir = $env:GHTOOLS_INITIAL_DIR
if ($initialDir -and (Test-Path $initialDir)) {
    $dialog.SelectedPath = $initialDir
}
$result = $dialog.ShowDialog($ownerForm)
$ownerForm.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.SelectedPath
}
'''

    env = os.environ.copy()
    env["GHTOOLS_INITIAL_DIR"] = initial_dir if initial_dir and os.path.isdir(initial_dir) else ""

    commands = [
        [
            "powershell",
            "-NoProfile",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        [
            "pwsh",
            "-NoProfile",
            "-STA",
            "-Command",
            script,
        ],
    ]

    for command in commands:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                check=False,
            )
        except FileNotFoundError:
            continue

        if completed.returncode not in (0, 1):
            continue

        selected = (completed.stdout or "").strip()
        if selected:
            return selected
        return ""

    return None


class ImageAutoloader(PreviewImage):
    """지정한 폴더에서 가장 최근(수정시간) 이미지를 자동으로 불러오는 노드."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "sort_by": (["time", "name"],),
                "sort_order": (["descending", "ascending"],),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "load_latest"
    CATEGORY = "🐴GHTools/Utils"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, folder_path="", sort_by="time", sort_order="descending", **kwargs):
        path = folder_path.strip().strip('"')
        if not path or not os.path.isdir(path):
            return ""
        target = _find_image(path, sort_by, sort_order)
        if target is None:
            return ""
        return f"{sort_by}_{sort_order}_{os.path.getmtime(target)}_{os.path.basename(target)}"

    def load_latest(self, folder_path="", sort_by="time", sort_order="descending",
                    prompt=None, extra_pnginfo=None):
        path = folder_path.strip().strip('"')
        if not path or not os.path.isdir(path):
            raise ValueError(f"유효하지 않은 폴더 경로: {folder_path}")

        target = _find_image(path, sort_by, sort_order)
        if target is None:
            raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {path}")

        img = Image.open(target)
        img = ImageOps.exif_transpose(img)

        if img.mode == "I":
            img = img.point(lambda i: i * (1 / 255))
        img_rgba = img.convert("RGBA")
        image_np = np.array(img_rgba).astype(np.float32) / 255.0

        rgb = torch.from_numpy(image_np[:, :, :3]).unsqueeze(0)
        mask = torch.from_numpy(image_np[:, :, 3]).unsqueeze(0)

        preview = self.save_images(rgb, "ghtools_autoload", prompt, extra_pnginfo)

        return {
            "ui": preview["ui"],
            "result": (rgb, mask),
        }


@PromptServer.instance.routes.post("/ghtools/image_autoloader_pick_folder")
async def handle_image_autoloader_pick_folder(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    initial_dir = str(data.get("folder_path", "")).strip().strip('"')

    try:
        selected = await asyncio.to_thread(_open_folder_picker, initial_dir)
    except Exception as exc:
        return web.json_response({"code": -1, "error": str(exc)})

    if not selected:
        return web.json_response({"code": 0, "folder_path": ""})

    return web.json_response({"code": 1, "folder_path": os.path.normpath(selected)})


@PromptServer.instance.routes.post("/ghtools/image_autoloader_preview")
async def handle_image_autoloader_preview(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    folder_path = str(data.get("folder_path", "")).strip().strip('"')
    if not folder_path or not os.path.isdir(folder_path):
        return web.json_response({"code": 0, "error": "Invalid folder path"})

    sort_by = str(data.get("sort_by", "time"))
    sort_order = str(data.get("sort_order", "descending"))
    target = _find_image(folder_path, sort_by, sort_order)
    if target is None:
        return web.json_response({"code": 0, "error": "No image found"})

    try:
        preview = await asyncio.to_thread(_create_preview_image_info, target)
    except Exception as exc:
        return web.json_response({"code": -1, "error": str(exc)})

    return web.json_response({"code": 1, "image": preview, "source_path": target})
