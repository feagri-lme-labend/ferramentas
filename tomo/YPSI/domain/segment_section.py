import cv2

def segment_section(result, blur_size, blur_sigma, threshold):

    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), blur_sigma)

    _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)

    binary[result[:,:,0] == 0] = 0

    return binary