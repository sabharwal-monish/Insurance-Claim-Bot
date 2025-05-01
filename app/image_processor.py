from PIL import Image

def process_image(image_path):
    image = Image.open(image_path)
    return "Car Damage Detected"
