import cv2
import numpy as np


def build_zoom_view(img_np, ponto, zoom_size, zoom_scale, w, h):

    px, py = int(ponto[0]), int(ponto[1])

    half = zoom_size // 2

    x1 = max(px - half, 0)
    y1 = max(py - half, 0)
    x2 = min(px + half, w)
    y2 = min(py + half, h)

    if x2 <= x1:
        x2 = x1 + 1

    if y2 <= y1:
        y2 = y1 + 1

    zoom_crop = np.ascontiguousarray(img_np[y1:y2, x1:x2])

    if zoom_crop.size == 0:
        zoom_crop = np.zeros((50, 50, 3), dtype=np.uint8)

    cv2.circle(zoom_crop, (px - x1, py - y1), 5, (0, 0, 255), -1)

    zoom_img = cv2.resize(
        zoom_crop,
        (zoom_crop.shape[1] * zoom_scale, zoom_crop.shape[0] * zoom_scale),
        interpolation=cv2.INTER_NEAREST
    )

    zx = (px - x1) * zoom_scale
    zy = (py - y1) * zoom_scale

    cv2.line(zoom_img, (0, zy), (zoom_img.shape[1], zy), (0, 255, 0), 3)
    cv2.line(zoom_img, (zx, 0), (zx, zoom_img.shape[0]), (0, 255, 0), 3)

    zoom_img_rgb = cv2.cvtColor(zoom_img, cv2.COLOR_BGR2RGB)

    return zoom_img_rgb