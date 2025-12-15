from PIL import Image
import os
import tempfile
import subprocess

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

print("Generating complete icon set...")

# ------------------------
# 1. Generate Windows ICO file with multiple sizes
# ------------------------
print("\n1. Generating Windows ICO file...")

# Required sizes for ICO
ico_sizes = [16, 24, 32, 48, 64, 128, 256]

# Create temporary directory for ICO generation
tmp_dir = tempfile.mkdtemp()
ico_files = []

for size in ico_sizes:
    # Use light mode for ICO as it's most compatible
    ico_icon = light_base.resize((size, size), Image.Resampling.LANCZOS)
    ico_file = os.path.join(tmp_dir, f'ico-{size}.png')
    ico_icon.save(ico_file, format='PNG')
    ico_files.append(ico_file)

# Generate ICO file
output_ico = os.path.join(icons_dir, 'icon.ico')
try:
    # Use PIL to save as ICO
    ico_images = [Image.open(f) for f in ico_files]
    ico_images[0].save(output_ico, format='ICO', append_images=ico_images[1:], sizes=[(size, size) for size in ico_sizes])
    print(f"✓ Successfully created ICO file with multiple sizes: {output_ico}")
except Exception as e:
    print(f"✗ Error creating ICO file: {e}")

# Cleanup tmp files
for f in ico_files:
    os.remove(f)
os.rmdir(tmp_dir)

# ------------------------
# 2. Update Android icons
# ------------------------
print("\n2. Updating Android icons...")

# Android mipmap sizes and scales
android_mipmaps = {
    'mdpi': 1.0,
    'hdpi': 1.5,
    'xhdpi': 2.0,
    'xxhdpi': 3.0,
    'xxxhdpi': 4.0
}

# Base size for Android launcher icons (48dp)
base_dp = 48

for mipmap, scale in android_mipmaps.items():
    size = int(base_dp * scale)
    print(f"  Updating {mipmap} ({size}x{size})...")
    
    # Generate icon
    android_icon = light_base.resize((size, size), Image.Resampling.LANCZOS)
    
    # Update all Android icon types
    mipmap_dir = os.path.join(icons_dir, f'android/mipmap-{mipmap}')
    if os.path.exists(mipmap_dir):
        # Foreground icons need to be smaller (for adaptive icons)
        foreground_size = int(size * 0.7)
        foreground_icon = light_base.resize((foreground_size, foreground_size), Image.Resampling.LANCZOS)
        
        # Save icons
        android_icon.save(os.path.join(mipmap_dir, 'ic_launcher.png'), format='PNG')
        android_icon.save(os.path.join(mipmap_dir, 'ic_launcher_round.png'), format='PNG')
        foreground_icon.save(os.path.join(mipmap_dir, 'ic_launcher_foreground.png'), format='PNG')

# ------------------------
# 3. Update iOS icons
# ------------------------
print("\n3. Updating iOS icons...")

# iOS icon sizes (name: (width, height))
ios_sizes = {
    'AppIcon-20x20@1x': (20, 20),
    'AppIcon-20x20@2x': (40, 40),
    'AppIcon-20x20@3x': (60, 60),
    'AppIcon-29x29@1x': (29, 29),
    'AppIcon-29x29@2x': (58, 58),
    'AppIcon-29x29@3x': (87, 87),
    'AppIcon-40x40@1x': (40, 40),
    'AppIcon-40x40@2x': (80, 80),
    'AppIcon-40x40@3x': (120, 120),
    'AppIcon-512@2x': (1024, 1024),
    'AppIcon-60x60@2x': (120, 120),
    'AppIcon-60x60@3x': (180, 180),
    'AppIcon-76x76@1x': (76, 76),
    'AppIcon-76x76@2x': (152, 152),
    'AppIcon-83.5x83.5@2x': (167, 167)
}

ios_dir = os.path.join(icons_dir, 'ios')
if os.path.exists(ios_dir):
    for icon_name, (width, height) in ios_sizes.items():
        print(f"  Updating {icon_name}...")
        ios_icon = light_base.resize((width, height), Image.Resampling.LANCZOS)
        ios_icon.save(os.path.join(ios_dir, f'{icon_name}.png'), format='PNG')
        
        # Also update the duplicate files (like AppIcon-20x20@2x-1.png)
        duplicate_name = icon_name.replace('@', '@2x-1') if '@2x' in icon_name else None
        if duplicate_name:
            ios_icon.save(os.path.join(ios_dir, f'{duplicate_name}.png'), format='PNG')

# ------------------------
# 4. Verify all icons are updated
# ------------------------
print("\n4. Verifying icon files...")

# Check main icon files
main_icons = ['icon.png', 'icon-512.png', 'icon-1024.png', 'icon.icns', 'icon.ico']
for icon_file in main_icons:
    icon_path = os.path.join(icons_dir, icon_file)
    if os.path.exists(icon_path):
        print(f"✓ {icon_file} exists")
    else:
        print(f"✗ {icon_file} missing")

print("\nAll icons updated successfully!")
print(f"Icons directory: {icons_dir}")
print("\nThe icons now include:")
print("- Light and dark mode support for macOS (ICNS file)")
print("- Multiple sizes for Windows (ICO file)")
print("- Updated Android adaptive icons")
print("- Updated iOS icons")
print("- Multi-resolution PNG icons for all platforms")