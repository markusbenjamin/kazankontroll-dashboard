from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from skimage import restoration, util

def process_image():
    # Open an image file
    with Image.open('heatmeter_images/image.jpg') as img:
        # Rotate the image
        full_image = img.transpose(Image.ROTATE_90)

        # Crop the image
        rotates = [0, 0, 0, 360 * 0.125 * 0.125 * 0]

        crop_rectangles = [
            (202, 293, 255, 322),
            (220, 496, 269, 526),
            (213, 694, 281, 722),
            (118, 25, 171, 59)
        ]

        brightness1_factors = [3, 3, 3, 0.5]
        contrast_factors = [2, 2, 2, 2]
        brightness2_factors = [1, 1, 1, 4]

        for cycle in range(1, 5):
            cycle_crop = full_image.crop(crop_rectangles[cycle - 1])
            #cycle_crop = cycle_crop.rotate(rotates[cycle - 1], expand=True, fillcolor='white')
            cycle_crop = cycle_crop.convert('L')

            # Adjust brightness and contrast
            enhancer = ImageEnhance.Contrast(cycle_crop)
            cycle_crop = enhancer.enhance(contrast_factors[cycle - 1])
            enhancer = ImageEnhance.Brightness(cycle_crop)
            cycle_crop = enhancer.enhance(brightness1_factors[cycle - 1])

            # Sharpen the image
            cycle_crop = cycle_crop.filter(ImageFilter.SHARPEN)

            # Convert Pillow image to NumPy array for denoising
            cycle_crop_np = np.array(cycle_crop)

            # Apply denoising
            cycle_crop_np = restoration.denoise_nl_means(cycle_crop_np, patch_size=7, patch_distance=11, h=0.1)
            
            cycle_crop = Image.fromarray(util.img_as_ubyte(cycle_crop_np))

            enhancer = ImageEnhance.Brightness(cycle_crop)
            cycle_crop = enhancer.enhance(brightness2_factors[cycle - 1])

            # Convert back to Pillow image and save
            cycle_crop.save(f'heatmeter_images/mod_image_{cycle}.jpg')

if __name__ == "__main__":
    process_image()