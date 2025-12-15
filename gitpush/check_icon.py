from PIL import Image
import os

# Open the current icon.png
current_icon_path = '/Users/wutiaoyun/Desktop/gitpush/gitpush-bridge/src-tauri/icons/icon.png'
current_icon = Image.open(current_icon_path)

# Get some pixels to understand the pattern
print('Current icon.png analysis:')
print(f'Size: {current_icon.size}')
print(f'Mode: {current_icon.mode}')

# Check center pixel and corners
center_x, center_y = current_icon.size[0] // 2, current_icon.size[1] // 2
pixels_to_check = [
    (10, 10),  # Top-left
    (current_icon.size[0] - 10, 10),  # Top-right
    (10, current_icon.size[1] - 10),  # Bottom-left
    (current_icon.size[0] - 10, current_icon.size[1] - 10),  # Bottom-right
    (center_x, center_y)  # Center
]

for x, y in pixels_to_check:
    pixel = current_icon.getpixel((x, y))
    print(f'Pixel at ({x},{y}): {pixel}')

# Check the round corner images
print('\nRound corner images:')
round_files = [
    '/Users/wutiaoyun/Desktop/gitpush/gitpush-bridge/src-tauri/icons/round_corner_image_by_atool.png',
    '/Users/wutiaoyun/Desktop/gitpush/gitpush-bridge/src-tauri/icons/round_corner_image_by_atool-2.png'
]

for img_path in round_files:
    if os.path.exists(img_path):
        img = Image.open(img_path)
        pixel = img.getpixel((100, 100))  # Check near center
        print(f'{os.path.basename(img_path)} - Center pixel: {pixel}')
        
        # Check if it has a white background by looking at multiple edge pixels
        has_white_bg = True
        for x in range(0, 20):
            for y in range(0, 20):
                edge_pixel = img.getpixel((x, y))
                if edge_pixel[:3] != (255, 255, 255):
                    has_white_bg = False
                    break
            if not has_white_bg:
                break
        print(f'  Has white background: {has_white_bg}')
        
        # Count non-transparent pixels to see the pattern
        non_transparent = 0
        for x in range(500, 524):
            for y in range(500, 524):
                p = img.getpixel((x, y))
                if p[3] > 0:
                    non_transparent += 1
        print(f'  Non-transparent pixels in 24x24 center area: {non_transparent}')

# Explain ICNS format
print('\nICNS Format Explanation:')
print('1. ICNS is a single file that contains multiple icon sizes for macOS')
print('2. It supports both light and dark modes within the same file')
print('3. The iconutil tool creates ICNS files from iconsets with appropriate naming')
print('4. For light/dark mode support, you need icons named with -light and -dark suffixes')
print('5. The current icon.icns might not have been generated with proper light/dark mode support')