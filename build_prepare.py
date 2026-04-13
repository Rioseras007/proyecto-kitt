from PIL import Image
import os

def convert_to_ico(png_path, ico_name="kitt.ico"):
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found")
        return
    img = Image.open(png_path)
    # Resize to common icon sizes
    img.save(ico_name, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icon saved as: {ico_name}")

if __name__ == "__main__":
    # Path to the generated png icon
    png_file = r"C:\Users\Alfonso\.gemini\antigravity\brain\4c7da0b0-1fe6-4923-ba78-46fb0b0d95e4\kitt_icon_1775451345957.png"
    convert_to_ico(png_file)
