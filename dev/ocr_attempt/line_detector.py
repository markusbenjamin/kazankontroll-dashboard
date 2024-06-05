from PIL import Image, ImageDraw
import numpy as np
import copy

# Perform Hough Transform to detect lines
def hough_line_detection(binary_img, theta_min, theta_max, theta_res, rho_res):
    thetas = np.deg2rad(np.arange(theta_min, theta_max, theta_res))
    # Rho ranges from the diagonal length of the image in negative to positive
    width, height = binary_img.shape
    diag_len = int(np.ceil(np.sqrt(width**2 + height**2)))
    rhos = np.linspace(-diag_len, diag_len, int(2 * diag_len / rho_res) + 1)

    # Cache some reusable values
    cos_t = np.cos(thetas)
    sin_t = np.sin(thetas)
    num_thetas = len(thetas)

    # Hough accumulator array of theta vs rho
    accumulator = np.zeros((len(rhos), num_thetas), dtype=np.uint64)
    y_idxs, x_idxs = np.nonzero(binary_img)  # (row, col) indexes to edges

    # Vote in the hough accumulator
    for i in range(len(x_idxs)):
        x = x_idxs[i]
        y = y_idxs[i]

        for t_idx in range(num_thetas):
            # Calculate rho. diag_len is added for a positive index
            rho_val = x * cos_t[t_idx] + y * sin_t[t_idx]
            rho_idx = int(round((rho_val + diag_len) / rho_res))
            accumulator[rho_idx, t_idx] += 1

    return accumulator, thetas, rhos

# Define a function to extract line segments from the accumulator
def find_lines(img, thresholding, theta_min, theta_max, theta_res, rho_res, detections_threshold):
    binary_image = np.array(img) > 255*thresholding
    accumulator, thetas, rhos = hough_line_detection(binary_image,theta_min, theta_max, theta_res, rho_res)
    line_endpoints = []
    for rho_idx in range(accumulator.shape[0]):
        for theta_idx in range(accumulator.shape[1]):
            if accumulator[rho_idx, theta_idx] > detections_threshold:
                rho = rhos[rho_idx]
                theta = thetas[theta_idx]
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                x1 = int(x0 + 1000 * (-b))
                y1 = int(y0 + 1000 * (a))
                x2 = int(x0 - 1000 * (-b))
                y2 = int(y0 - 1000 * (a))
                line_endpoints.append(((x1, y1), (x2, y2)))
    return line_endpoints

def find_intersection(line1, line2):
    # Each line is represented as ((x1, y1), (x2, y2))
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    # Calculate the slopes (m1, m2) and y-intercepts (c1, c2) of the lines
    m1 = (y2 - y1) / float(x2 - x1) if x2 != x1 else float('inf')
    m2 = (y4 - y3) / float(x4 - x3) if x4 != x3 else float('inf')
    c1 = y1 - m1 * x1
    c2 = y3 - m2 * x3

    # If the slopes are equal, the lines are parallel (or coincident)
    if m1 == m2:
        return None

    # Find the intersection point
    x_intersect = (c2 - c1) / float(m1 - m2)
    y_intersect = m1 * x_intersect + c1

    return (x_intersect, y_intersect)

# Draw the lines on the image
def draw_lines(image, lines):
    draw = ImageDraw.Draw(image)
    for line in lines:
        draw.line(line, fill=255, width=2)
    return image

def draw_points(image, points, point_size=5):
    draw = ImageDraw.Draw(image)
    for point in points:
        x, y = point
        bounding_box = [x - point_size // 2, y - point_size // 2, x + point_size // 2, y + point_size // 2]
        draw.ellipse(bounding_box, fill=255)
    return image

def find_significant_points(img):
    width, height = img.size
    h_lines = find_lines(copy.deepcopy(img), 0.5, 80, 100, 1, 1, 40)
    v_lines = find_lines(copy.deepcopy(img), 0.5, -10, 10, 1, 1, 58)
    draw_lines(draw_lines(copy.deepcopy(img), v_lines),h_lines).save("detected_lines.jpg")
    intersects = []
    for line1 in v_lines:
        for line2 in h_lines:
            intersects.append(np.round(find_intersection(line1,line2)))

    x_res, y_res = round(width/10), round(height/10)  # Change these values as needed

    # List to hold average positions
    averaged_intersects = []

    # Iterate over the image with the set resolution
    for y in range(0, height, y_res):
        for x in range(0, width, x_res):
            # Collect points that lie within the current section
            section_points = [point for point in intersects if x <= point[0] < x + x_res and y <= point[1] < y + y_res]

            # Calculate the average position of points in the section, if any
            if section_points:
                avg_position = np.mean(section_points, axis=0)
                averaged_intersects.append(avg_position)
    
    return averaged_intersects

if __name__ == "__main__":
    with Image.open("extraction.jpg") as img:
        draw_points(img,find_significant_points(img)).save("intersection_points.jpg")