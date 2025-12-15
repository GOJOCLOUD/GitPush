#!/usr/bin/env python3
"""
生成并替换 GitPush 应用的图标
白色背景用于浅色模式，黑色背景用于深色模式
"""

from PIL import Image
import os
import shutil

def generate_icon_with_background(icon_path, background_color, output_path, size):
    """
    生成带有指定背景颜色的图标
    
    Args:
        icon_path: 原始图标路径
        background_color: 背景颜色 (r, g, b, a)
        output_path: 输出路径
        size: 输出尺寸
    """
    # 打开原始图标
    icon = Image.open(icon_path).convert("RGBA")
    
    # 创建新的背景
    background = Image.new("RGBA", (size, size), background_color)
    
    # 调整图标大小以适应背景，保持比例
    icon.thumbnail((size, size), Image.Resampling.LANCZOS)
    
    # 计算图标在背景上的位置（居中）
    icon_x = (size - icon.width) // 2
    icon_y = (size - icon.height) // 2
    
    # 将图标粘贴到背景上
    background.paste(icon, (icon_x, icon_y), icon)
    
    # 保存生成的图标
    background.save(output_path, format="PNG")
    
    print(f"✅ 生成: {output_path} ({size}x{size})")
    
    # 关闭图片
    icon.close()
    background.close()

def main():
    # 定义文件路径
    light_bg_icon = "light_bg_icon.png"
    dark_bg_icon = "dark_bg_icon.png"
    icons_dir = "src-tauri/icons/"
    
    # 确保图标目录存在
    os.makedirs(icons_dir, exist_ok=True)
    
    print("=== GitPush 图标生成脚本 ===")
    
    # 1. 首先保存原始图标（1024x1024）
    generate_icon_with_background(light_bg_icon, (255, 255, 255, 255), os.path.join(icons_dir, "icon-1024-light.png"), 1024)
    generate_icon_with_background(dark_bg_icon, (0, 0, 0, 255), os.path.join(icons_dir, "icon-1024-dark.png"), 1024)
    
    # 2. 生成各种分辨率的图标
    resolutions = [
        32,    # 32x32.png
        64,    # 64x64.png
        128,   # 128x128.png
        256,   # 128x128@2x.png
    ]
    
    for size in resolutions:
        # 生成浅色模式图标
        output_name = f"{size}x{size}.png" if size != 256 else "128x128@2x.png"
        generate_icon_with_background(light_bg_icon, (255, 255, 255, 255), os.path.join(icons_dir, output_name), size)
        
        # 生成深色模式图标
        output_name_dark = f"{size}x{size}-dark.png" if size != 256 else "128x128@2x-dark.png"
        generate_icon_with_background(dark_bg_icon, (0, 0, 0, 255), os.path.join(icons_dir, output_name_dark), size)
    
    # 3. 复制主图标
    shutil.copy2(os.path.join(icons_dir, "icon-1024-light.png"), os.path.join(icons_dir, "icon-1024.png"))
    shutil.copy2(os.path.join(icons_dir, "128x128.png"), os.path.join(icons_dir, "icon.png"))
    
    print("\n✅ 所有图标生成完成！")
    print("\n接下来需要手动更新 Tauri 配置，以支持深色/浅色模式切换。")

if __name__ == "__main__":
    main()
