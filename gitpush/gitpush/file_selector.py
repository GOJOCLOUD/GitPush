#!/usr/bin/env python3
import subprocess
import platform
import logging
from pathlib import Path
from errors import FileSelectError
from logger import log

# 只在需要时导入 tkinter，避免在不需要的平台上出现问题
def _choose_file_other():
    """在 Windows/Linux 上使用 tkinter 选择文件或文件夹"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 先尝试选择文件
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=[("All Files", "*.*")]
        )
        
        if file_path:
            selected_path = Path(file_path).resolve()
            log(f"选择文件: {selected_path}")
            return selected_path
        
        # 如果用户取消了文件选择，尝试选择文件夹
        folder_path = filedialog.askdirectory(
            title="选择文件夹"
        )
        
        if folder_path:
            selected_path = Path(folder_path).resolve()
            log(f"选择文件夹: {selected_path}")
            return selected_path
        
        return None
    except ImportError as e:
        log(f"无法导入 tkinter: {e}", level=logging.ERROR)
        raise FileSelectError("无法导入 tkinter，无法选择文件")
    except Exception as e:
        log(f"文件选择失败: {e}", level=logging.ERROR)
        raise FileSelectError(f"文件选择失败: {e}")


def _choose_file_macos():
    """在 macOS 上使用 AppleScript 选择文件或文件夹"""
    # 先尝试选择文件
    file_cmd = ["osascript", "-e", 'POSIX path of (choose file with prompt "选择要上传的文件或文件夹")']
    try:
        result = subprocess.run(file_cmd, capture_output=True, text=True, check=True)
        file_path = result.stdout.strip()
        if file_path:
            selected_path = Path(file_path).resolve()
            log(f"选择文件: {selected_path}")
            return selected_path
    except subprocess.CalledProcessError:
        # 用户取消了文件选择，尝试选择文件夹
        folder_cmd = ["osascript", "-e", 'POSIX path of (choose folder with prompt "选择要上传的文件或文件夹")']
        try:
            result = subprocess.run(folder_cmd, capture_output=True, text=True, check=True)
            folder_path = result.stdout.strip()
            if folder_path:
                selected_path = Path(folder_path).resolve()
                log(f"选择文件夹: {selected_path}")
                return selected_path
        except subprocess.CalledProcessError:
            # 用户取消了文件夹选择
            return None
    except Exception as e:
        log(f"文件选择失败: {e}", level=logging.ERROR)
        raise FileSelectError(f"文件选择失败: {e}")
    
    return None


def choose_upload_path():
    """跨平台选择文件或文件夹"""
    log("请选择要上传的文件或文件夹...")
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            upload_path = _choose_file_macos()
        else:  # Windows/Linux
            upload_path = _choose_file_other()
        
        if not upload_path:
            log("错误: 未选择任何文件或文件夹", level=logging.ERROR)
            raise FileSelectError("未选择任何文件或文件夹")
        
        # 检查路径是否存在
        if not upload_path.exists():
            log(f"错误: 上传路径不存在: {upload_path}", level=logging.ERROR)
            raise FileSelectError(f"上传路径不存在: {upload_path}")
        
        log(f"上传路径验证成功: {upload_path}")
        return upload_path
    except FileSelectError:
        raise
    except Exception as e:
        log(f"文件选择过程中发生错误: {e}", level=logging.ERROR)
        raise FileSelectError(f"文件选择过程中发生错误: {e}")
