#!/usr/bin/env python3
"""
将round_corner_image_by_atool.png处理为正方形，然后替换所有其他图标
使用方法：
1. 确保已安装Pillow库：pip3 install pillow
2. 运行：python3 process_and_replace_icons.py
"""

from PIL import Image
import os
import shutil

def process_image(input_path, output_path, target_size=1024):
    """将图片处理为正方形，保持圆角效果"""
    print(f"正在处理图片: {input_path}")
    
    # 打开图片
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    
    print(f"原始尺寸: {width}x{height}")
    
    # 直接拉伸图片到正方形，保持圆角效果
    square_img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    
    # 保存处理后的图片
    square_img.save(output_path, format="PNG")
    
    print(f"处理后的尺寸: {target_size}x{target_size}")
    print(f"保存到: {output_path}")
    
    return output_path

def replace_all_icons(source_path, icons_dir):
    """将所有图标替换为处理后的图片"""
    print(f"\n正在替换所有图标...")
    
    # 定义需要替换的图标文件列表
    icon_files = [
        "32x32.png",
        "128x128.png",
        "128x128@2x.png",
        "icon.png"
    ]
    
    # 打开处理后的图片
    source_img = Image.open(source_path).convert("RGBA")
    
    # 替换每个图标
    for filename in icon_files:
        output_path = os.path.join(icons_dir, filename)
        
        # 解析文件名中的尺寸
        if "@2x" in filename:
            # 128x128@2x.png 对应 256x256
            size = 256
        else:
            # 32x32.png 对应 32x32, 128x128.png 对应 128x128, icon.png 对应 128x128
            size = int(filename.split("x")[0]) if "x" in filename else 128
        
        # 调整图片大小
        resized_img = source_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # 保存替换后的图标
        resized_img.save(output_path, format="PNG")
        
        print(f"✅ 已替换: {filename} (尺寸: {size}x{size})")
    
    # 关闭源图片
    source_img.close()
    
    print(f"\n✅ 所有图标已替换完成！")

def main():
    # 定义文件路径
    input_image = "src-tauri/icons/round_corner_image_by_atool.png"
    temp_square_image = "src-tauri/icons/temp_square.png"
    icons_dir = "src-tauri/icons/"
    
    print("=== 图片处理和图标替换脚本 ===")
    print("将round_corner_image_by_atool.png处理为正方形，然后替换所有其他图标")
    
    # 1. 处理图片为正方形
    square_image = process_image(input_image, temp_square_image, target_size=1024)
    
    # 2. 替换所有其他图标
    replace_all_icons(square_image, icons_dir)
    
    # 3. 清理临时文件
    if os.path.exists(temp_square_image):
        os.remove(temp_square_image)
        print(f"\n已清理临时文件: {temp_square_image}")
    
    # 4. 显示最终图标列表
    print(f"\n=== 最终图标文件 ===")
    for file in os.listdir(icons_dir):
        if file.endswith(".png") or file.endswith(".icns") or file.endswith(".ico"):
            file_path = os.path.join(icons_dir, file)
            size = os.path.getsize(file_path)
            print(f"  {file} ({size} bytes)")
    
    print(f"\n✅ 操作完成！")
    print(f"接下来可以重启应用查看效果:")
    print(f"   npm run tauri dev")

if __name__ == "__main__":
    main()
