#!/usr/bin/env python3
"""
将用户提供的圆角图片裁剪为正方形，然后生成Tauri图标
使用方法：
1. 确保已安装Pillow库：pip3 install pillow
2. 运行：python3 crop_and_generate_icons.py
"""

from PIL import Image
import os
import subprocess

def crop_to_square(image_path, output_path):
    """将图片裁剪为正方形"""
    print(f"正在裁剪图片: {image_path}")
    
    # 打开图片
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    print(f"原始尺寸: {width}x{height}")
    
    # 计算正方形尺寸（取最小边）
    size = min(width, height)
    
    # 计算裁剪区域（居中裁剪）
    left = (width - size) // 2
    top = (height - size) // 2
    right = left + size
    bottom = top + size
    
    # 裁剪图片
    square_img = img.crop((left, top, right, bottom))
    
    # 保存裁剪后的图片
    square_img.save(output_path, format="PNG")
    
    print(f"裁剪后的尺寸: {size}x{size}")
    print(f"保存到: {output_path}")
    
    return output_path

def generate_tauri_icons(source_path):
    """使用Tauri生成所有图标"""
    print(f"\n正在生成Tauri图标...")
    
    # 运行tauri icon命令
    result = subprocess.run(
        ["tauri", "icon", source_path],
        cwd="/Users/wutiaoyun/Desktop/gitpush/gitpush-bridge",
        capture_output=True,
        text=True
    )
    
    # 输出结果
    if result.returncode == 0:
        print("✅ Tauri图标生成成功！")
        print("生成的图标:")
        print(result.stdout)
    else:
        print("❌ Tauri图标生成失败:")
        print(result.stderr)
    
    return result.returncode == 0

def clean_up_temp_files(file_path):
    """清理临时文件"""
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"\n已清理临时文件: {file_path}")

def main():
    # 定义文件路径
    input_image = "src-tauri/icons/round_corner_image_by_atool.png"
    temp_square_image = "src-tauri/icons/temp_square_icon.png"
    
    print("=== 图标生成脚本 ===")
    
    # 1. 裁剪为正方形
    square_image = crop_to_square(input_image, temp_square_image)
    
    # 2. 生成Tauri图标
    success = generate_tauri_icons(square_image)
    
    # 3. 清理临时文件
    clean_up_temp_files(temp_square_image)
    
    if success:
        print("\n✅ 所有图标已成功生成！")
        print("\n接下来可以查看生成的图标:")
        print("   ls -la src-tauri/icons/")
        return True
    else:
        print("\n❌ 图标生成失败！")
        return False

if __name__ == "__main__":
    main()
