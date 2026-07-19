import os
from PIL import Image, ImageDraw

def main():
    icon_path = 'assets/app_icon.png'
    if not os.path.exists(icon_path):
        print(f"Error: Icon {icon_path} not found.")
        return
        
    im = Image.open(icon_path).convert("RGBA")
    
    # Crop the 32-pixel white border all around to get the main 960x960 icon content
    left = 32
    top = 32
    right = 1024 - 32
    bottom = 1024 - 32
    
    cropped = im.crop((left, top, right, bottom))
    
    # Resize back to 1024x1024 for standard premium resolution
    resized = cropped.resize((1024, 1024), Image.Resampling.LANCZOS)
    
    # Create a mask for rounded corners (macOS standard squircle style)
    mask = Image.new('L', (1024, 1024), 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw rounded rectangle mask
    # 230px radius gives a premium smooth squircle look
    draw.rounded_rectangle([0, 0, 1024, 1024], radius=230, fill=255)
    
    # Apply mask as alpha channel
    resized.putalpha(mask)
    
    # Save the file (overwrite the original app_icon.png)
    resized.save(icon_path, "PNG")
    print(f"Successfully cropped white border, applied rounded corners, and saved to {icon_path}")

if __name__ == "__main__":
    main()
