from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
from skimage import restoration, util
from scipy.ndimage import zoom
import copy
import os

def shift_array(array, shift_x_ratio, shift_y_ratio, fill_value=255):
    shift_x_ratio *= -1
    shift_y_ratio *= -1
    height, width = array.shape
    shift_x = int(width * shift_x_ratio)
    shift_y = int(height * shift_y_ratio)

    # Create an array filled with the fill_value
    shifted_array = np.full_like(array, fill_value)

    # Calculate the new coordinates after shifting
    start_x = max(0, -shift_x)
    end_x = min(width, width - shift_x)
    start_y = max(0, -shift_y)
    end_y = min(height, height - shift_y)

    # Assign the shifted values
    shifted_array[start_y:end_y, start_x:end_x] = array[max(0, shift_y):min(height, height + shift_y), max(0, shift_x):min(width, width + shift_x)]

    return shifted_array

def zoom_array(array, pad_ratio, fill_value=255):
    height, width = array.shape
    pad_height = int(height * abs(pad_ratio))
    pad_width = int(width * abs(pad_ratio))

    if pad_ratio == 0:
        return array
    else:
        if pad_ratio > 0:
            # Pad the array
            padded_or_cropped_array = np.pad(array, ((pad_height, pad_height), (pad_width, pad_width)), mode='constant', constant_values=fill_value)
        elif pad_ratio <0:
            # Crop the array
            padded_or_cropped_array = array[pad_height:-pad_height, pad_width:-pad_width]
            if padded_or_cropped_array.size == 0:
                raise ValueError("Cropping too much - resulting array is empty.")

        # Calculate new zoom factors to resize back to original dimensions
        zoom_factor_y = height / padded_or_cropped_array.shape[0]
        zoom_factor_x = width / padded_or_cropped_array.shape[1]

        # Resize the array
        resized_array = zoom(padded_or_cropped_array, (zoom_factor_y, zoom_factor_x))

        return resized_array

def seven_segment_ocr(unknown_vector_2D,archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18, h_shift_min=0,h_shift_max=0.25,h_shift_step=0.05,v_shift_min=-0.1,v_shift_max=0.1,v_shift_step=0.05,zoom_min=0.05,zoom_max=0.25,zoom_step=0.05):
    resized_archetype_vectors_2D = []
    archetype_dimensions = archetype_vectors_2D[0].shape
    unknown_dimensions = unknown_vector_2D.shape
    for archetype_vector_2D in archetype_vectors_2D:
        resized_archetype_vectors_2D.append(zoom(archetype_vector_2D, (unknown_dimensions[0] / archetype_dimensions[0], unknown_dimensions[1] / archetype_dimensions[1])))
    
    activations = []
    for h_shift in np.arange(h_shift_min,h_shift_max+h_shift_step,h_shift_step):
        for v_shift in np.arange(v_shift_min,v_shift_max+v_shift_step,v_shift_step):
            for zoom_level in np.arange(zoom_min,zoom_max+zoom_step,zoom_step):
                #segment_pixels = np.where(shift_array(zoom_array(copy.deepcopy(resized_archetype_vectors_2D[8]), zoom_level),h_shift,v_shift).flatten() == 0)[0]
                activation = {}
                for num in np.arange(0,10,1):
                    archetype_vector = 1 - (shift_array(zoom_array(copy.deepcopy(resized_archetype_vectors_2D[num]), zoom_level),h_shift,v_shift).flatten())/255
                    unknown_vector = 1 - unknown_vector_2D.flatten()/255
                    #activation[num] = np.mean([
                    #    np.dot(archetype_vector,unknown_vector)/np.mean([np.sum(archetype_vector),np.sum(unknown_vector)])*match_weights[num],
                    #    np.sum(archetype_vector[segment_pixels]==unknown_vector[segment_pixels])/len(segment_pixels)*diff_weights[num]
                    #])
                    activation[num] = np.dot(archetype_vector,unknown_vector)/np.mean([np.sum(archetype_vector),np.sum(unknown_vector)])
                activations.append(activation)

    def activation_checks(activation_as_array):
        gradient = abs(np.diff(np.sort(activation_as_array)))
        if total_da_threshold < sum(gradient) and da1_threshold < gradient[-1]:
            return True
        else:
            return False

    passed_activations = [activation for activation in activations if activation_checks(np.array(list(activation.values())))]

    predictions = []
    for activation in passed_activations:
        predictions.append(np.argmax(list(activation.values())))

    if 0<len(predictions):
        prediction = max(predictions, key=predictions.count)
    else:
        prediction = -1

    return prediction


if __name__ == "__main__":        
    archetype_vectors_2D = []
    for n in np.arange(0,10,1):
        with Image.open(f'archetypes/archetype_{n}.png') as img:
            archetype_vectors_2D.append(np.array(img.convert('L')))

    
    #match_weights = {
    #    0:1,
    #    1:1,
    #    2:1,
    #    3:1,
    #    4:1,
    #    5:1,
    #    6:1,
    #    7:1,
    #    8:1,
    #    9:1
    #}
#
    #diff_weights = {
    #    0:0,
    #    1:0,
    #    2:0,
    #    3:0,
    #    4:0,
    #    5:0,
    #    6:0,
    #    7:0,
    #    8:0,
    #    9:0
    #}

    for char_img in [file for file in os.listdir('batch/chars') if file.lower().endswith('.jpg')]:
        with Image.open(f"batch/chars/{char_img}") as img:
            unknown_vector_2D = np.array(img)
            prediction = seven_segment_ocr(unknown_vector_2D,archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18)
            if not os.path.exists(f'preds/{prediction}'):
                os.makedirs(f'preds/{prediction}')
            img.save(f'preds/{prediction}/{char_img}.jpg')
