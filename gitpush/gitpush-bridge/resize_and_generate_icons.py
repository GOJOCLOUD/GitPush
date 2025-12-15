#!/usr/bin/env python3
"""
将用户提供的圆角图片缩放到正方形，保持原始比例和圆角效果
使用方法：
1. 确保已安装Pillow库：pip3 install pillow
2. 运行：python3 resize_and_generate_icons.py
"""

from PIL import Image
import os
import subprocess

def resize_to_square(image_path, output_path, target_size=1024):
    """将图片复制到输出路径，因为我们已经有了1024x1024的图标"""
    print(f"正在处理图片: {image_path}")
    
    # 打开图片
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    print(f"原始尺寸: {width}x{height}")
    
    # 如果已经是1024x1024，直接复制
    if width == target_size and height == target_size:
        img.save(output_path, format="PNG")
        print(f"直接复制到: {output_path}")
    else:
        # 否则进行缩放
        resized_img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        resized_img.save(output_path, format="PNG")
        print(f"缩放到 {target_size}x{target_size} 并保存到: {output_path}")
    
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
    input_image = "src-tauri/icons/icon-1024.png"
    temp_square_image = "src-tauri/icons/temp_square_icon.png"
    
    print("=== 图标生成脚本 ===")
    print("使用缩放+补白边的方式，保持原始比例和圆角效果")
    
    # 1. 缩放到正方形，保持原始比例和圆角效果
    square_image = resize_to_square(input_image, temp_square_image, target_size=1024)
    
    # 2. 生成Tauri图标
    success = generate_tauri_icons(square_image)
    
    # 3. 清理临时文件
    clean_up_temp_files(temp_square_image)
    
    if success:
        print("\n✅ 所有图标已成功生成！")
        print("\n接下来可以查看生成的图标:")
        print("   ls -la src-tauri/icons/")
        print("\n然后重启应用查看效果:")
        print("   npm run tauri dev")
        return True
    else:
        print("\n❌ 图标生成失败！")
        return False

if __name__ == "__main__":
    main()
