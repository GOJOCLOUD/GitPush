#!/usr/bin/env python3
"""
全面替换所有图标，包括iOS和Android目录
使用用户提供的圆角图片，不切割，可缩放
"""

from PIL import Image
import os
import glob

def get_all_png_files(icons_dir):
    """
    获取icons目录下所有的PNG文件，包括子目录
    
    Args:
        icons_dir: 图标目录
    
    Returns:
        list: PNG文件路径列表
    """
    png_files = []
    for root, dirs, files in os.walk(icons_dir):
        for file in files:
            if file.lower().endswith('.png'):
                png_files.append(os.path.join(root, file))
    return png_files

def determine_light_dark_images(icons_dir):
    """
    确定哪个是浅色模式图片，哪个是深色模式图片
    
    Args:
        icons_dir: 图标目录
    
    Returns:
        tuple: (light_image, dark_image)
    """
    # 获取两个round开头的图片
    round_images = glob.glob(os.path.join(icons_dir, 'round_corner_image_by_atool*.png'))
    
    if len(round_images) != 2:
        print(f"❌ 错误：找到 {len(round_images)} 个round开头的图片，需要2个")
        exit(1)
    
    img1 = round_images[0]
    img2 = round_images[1]
    
    # 获取文件大小，通常浅色图片文件较小
    size1 = os.path.getsize(img1)
    size2 = os.path.getsize(img2)
    
    print(f"找到圆角图片：")
    print(f"  {os.path.basename(img1)} - {size1} bytes")
    print(f"  {os.path.basename(img2)} - {size2} bytes")
    
    if size1 < size2:
        return (img1, img2)
    else:
        return (img2, img1)

def replace_icon_with_rounded_image(source_image, target_image_path):
    """
    用圆角图片替换目标图标
    
    Args:
        source_image: 源圆角图片路径
        target_image_path: 目标图标路径
    """
    # 打开源图片和目标图片
    source = Image.open(source_image)
    target_size = Image.open(target_image_path).size
    
    # 调整源图片大小以适应目标尺寸，不切割
    # 使用Image.Resampling.LANCZOS保持高质量
    resized = source.resize(target_size, Image.Resampling.LANCZOS)
    
    # 保存替换后的图标
    resized.save(target_image_path, format="PNG")
    
    # 关闭图片
    source.close()
    resized.close()
    
    print(f"✅ 替换: {os.path.relpath(target_image_path, 'src-tauri/icons/')}")

def main():
    icons_dir = "src-tauri/icons/"
    
    print("=== 全面替换所有图标脚本 ===")
    print("替换icons目录下所有PNG图标，包括iOS和Android子目录")
    
    # 1. 确定浅色和深色模式图片
    light_img, dark_img = determine_light_dark_images(icons_dir)
    print(f"\n✅ 浅色模式图片: {os.path.basename(light_img)}")
    print(f"✅ 深色模式图片: {os.path.basename(dark_img)}")
    
    # 2. 获取所有PNG文件
    all_png_files = get_all_png_files(icons_dir)
    print(f"\n找到 {len(all_png_files)} 个PNG文件")
    
    # 3. 替换所有图标
    print("\n=== 开始替换图标 ===")
    
    # 定义要跳过的文件（源文件本身）
    skip_files = [light_img, dark_img]
    skip_files = [os.path.abspath(f) for f in skip_files]
    
    for png_file in all_png_files:
        png_file_abs = os.path.abspath(png_file)
        
        # 跳过源文件本身
        if png_file_abs in skip_files:
            print(f"⏭️  跳过源文件: {os.path.relpath(png_file, 'src-tauri/icons/')}")
            continue
        
        # 替换图标
        # 根据文件名判断使用浅色还是深色模式图片
        if 'dark' in png_file.lower():
            replace_icon_with_rounded_image(dark_img, png_file)
        else:
            replace_icon_with_rounded_image(light_img, png_file)
    
    print("\n✅ 所有图标替换完成！")
    print("\n=== 最终结果 ===")
    print(f"替换了 {len(all_png_files) - 2} 个图标")
    print(f"使用了 {os.path.basename(light_img)} 作为浅色模式图标")
    print(f"使用了 {os.path.basename(dark_img)} 作为深色模式图标")
    print("\n接下来可以重启应用查看效果:")
    print("   npm run tauri dev")

if __name__ == "__main__":
    main()
