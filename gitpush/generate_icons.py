from PIL import Image
import os

# Paths
icons_dir = '/Users/wutiaoyun/Desktop/gitpush/gitpush-bridge/src-tauri/icons'
dark_icon_path = os.path.join(icons_dir, 'round_corner_image_by_atool.png')
light_icon_path = os.path.join(icons_dir, 'round_corner_image_by_atool-2.png')

# Verify input files exist
if not os.path.exists(dark_icon_path):
    print(f"Error: Dark icon not found at {dark_icon_path}")
    exit(1)
if not os.path.exists(light_icon_path):
    print(f"Error: Light icon not found at {light_icon_path}")
    exit(1)

# Open the base icons
dark_base = Image.open(dark_icon_path)
light_base = Image.open(light_icon_path)

# Required sizes for Tauri icons
sizes = [
    16, 32, 48, 64, 128, 256, 512, 1024
]

print("Generating multi-resolution icons...")

# Generate icons for each size
for size in sizes:
    print(f"Generating {size}x{size} icons...")
    
    # 计算缩小后的图标大小（原来的80%）
    # 我们需要在保留透明背景的情况下，将图标内容缩小到原来的80%
    
    # 生成浅色模式图标
    light_icon = light_base.resize((size, size), Image.Resampling.LANCZOS)
    
    # 创建一个新的透明背景图像
    transparent_bg = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # 计算缩小后的图标尺寸（80%）
    scaled_size = int(size * 0.8)
    
    # 将图标内容缩小到80%
    light_scaled = light_icon.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS)
    
    # 计算居中位置
    x = (size - scaled_size) // 2
    y = (size - scaled_size) // 2
    
    # 将缩小后的图标粘贴到透明背景的中央
    transparent_bg.paste(light_scaled, (x, y), light_scaled)
    
    # 保存最终图标
    transparent_bg.save(os.path.join(icons_dir, f'light-{size}.png'), format='PNG')
    
    # 同样处理深色模式图标（用户要求统一使用白底）    
    dark_icon = light_base.resize((size, size), Image.Resampling.LANCZOS)
    
    # 创建一个新的透明背景图像
    dark_transparent_bg = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # 将图标内容缩小到80%
    dark_scaled = dark_icon.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS)
    
    # 将缩小后的图标粘贴到透明背景的中央
    dark_transparent_bg.paste(dark_scaled, (x, y), dark_scaled)
    
    # 保存最终图标
    dark_transparent_bg.save(os.path.join(icons_dir, f'dark-{size}.png'), format='PNG')

def create_scaled_icon(icon, size):
    """
    创建缩放后的图标，将图标内容缩小到80%并居中显示在透明背景上
    
    Args:
        icon: PIL Image对象
        size: 输出图标尺寸
    
    Returns:
        PIL Image对象: 处理后的图标
    """
    # 创建一个新的透明背景图像
    transparent_bg = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # 计算缩小后的图标尺寸（80%）
    scaled_size = int(size * 0.8)
    
    # 将图标内容缩小到80%
    scaled = icon.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS)
    
    # 计算居中位置
    x = (size - scaled_size) // 2
    y = (size - scaled_size) // 2
    
    # 将缩小后的图标粘贴到透明背景的中央
    transparent_bg.paste(scaled, (x, y), scaled)
    
    return transparent_bg

# Generate the main icon files (使用白底图标，图标内容缩小到80%)
print("\nGenerating main icon files...")

# Generate main icon.png (128x128, 图标内容缩小到80%)
light_128 = light_base.resize((128, 128), Image.Resampling.LANCZOS)
scaled_icon = create_scaled_icon(light_128, 128)
scaled_icon.save(os.path.join(icons_dir, 'icon.png'), format='PNG')

# Generate icon-512.png and icon-1024.png (图标内容缩小到80%)
light_512 = light_base.resize((512, 512), Image.Resampling.LANCZOS)
scaled_512 = create_scaled_icon(light_512, 512)
scaled_512.save(os.path.join(icons_dir, 'icon-512.png'), format='PNG')

light_1024 = light_base.resize((1024, 1024), Image.Resampling.LANCZOS)
scaled_1024 = create_scaled_icon(light_1024, 1024)
scaled_1024.save(os.path.join(icons_dir, 'icon-1024.png'), format='PNG')

# Generate 32x32, 64x64, 128x128@2x for base icons (图标内容缩小到80%)
light_32 = light_base.resize((32, 32), Image.Resampling.LANCZOS)
scaled_32 = create_scaled_icon(light_32, 32)
scaled_32.save(os.path.join(icons_dir, '32x32.png'), format='PNG')

light_64 = light_base.resize((64, 64), Image.Resampling.LANCZOS)
scaled_64 = create_scaled_icon(light_64, 64)
scaled_64.save(os.path.join(icons_dir, '64x64.png'), format='PNG')

light_128x2 = light_base.resize((256, 256), Image.Resampling.LANCZOS)
scaled_128x2 = create_scaled_icon(light_128x2, 256)
scaled_128x2.save(os.path.join(icons_dir, '128x128@2x.png'), format='PNG')

print("\nIcon generation completed!")
print(f"Generated icons saved to {icons_dir}")

# Now create ICNS with light/dark mode support
print("\nCreating ICNS file with light/dark mode support...")

# Create temporary iconset directory
import tempfile
import subprocess

iconset_dir = tempfile.mkdtemp() + '.iconset'
os.makedirs(iconset_dir, exist_ok=True)

# Required sizes for ICNS with light/dark mode
icns_sizes = [
    (16, 1), (16, 2),
    (32, 1), (32, 2),
    (64, 1), (64, 2),
    (128, 1), (128, 2),
    (256, 1), (256, 2),
    (512, 1), (512, 2),
    (1024, 1), (1024, 2)
]

# Generate icons for ICNS (使用白底图标，图标内容缩小到80%)
for size, scale in icns_sizes:
    actual_size = size * scale
    
    # Generate icon for default/aqua appearance (使用白底图标，图标内容缩小到80%)
    light_icns = light_base.resize((actual_size, actual_size), Image.Resampling.LANCZOS)
    scaled_icns = create_scaled_icon(light_icns, actual_size)
    scaled_icns.save(os.path.join(iconset_dir, f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'), format='PNG')
    
    # Generate icon for darkAqua appearance (同样使用白底图标，图标内容缩小到80%)    
    light_icns_dark = light_base.resize((actual_size, actual_size), Image.Resampling.LANCZOS)
    scaled_icns_dark = create_scaled_icon(light_icns_dark, actual_size)
    scaled_icns_dark.save(os.path.join(iconset_dir, f'icon_{size}x{size}{"@2x" if scale == 2 else ""}-dark.png'), format='PNG')

# Generate ICNS file using iconutil
output_icns = os.path.join(icons_dir, 'icon.icns')
try:
    subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', output_icns], check=True)
    print(f"✓ Successfully created ICNS file with light/dark mode support: {output_icns}")
except subprocess.CalledProcessError as e:
    print(f"✗ Error creating ICNS file: {e}")
except FileNotFoundError:
    print("✗ Error: iconutil command not found (macOS only)")

# Cleanup
try:
    import shutil
    shutil.rmtree(iconset_dir.replace('.iconset', ''))
except:
    pass

print("\nAll tasks completed!")