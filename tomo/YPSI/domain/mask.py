import numpy as np
import cv2


def apply_polygon_mask(img, pts):

    h, w = img.shape[:2]

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, pts, 255)

    result = img.copy()
    result[mask == 0] = 0

    return result