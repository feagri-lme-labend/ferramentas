import cv2

def auto_resize_image(img_np, max_dim=10000):

    h, w = img_np.shape[:2]
    scale_img = 1.0
    resized = False

    if max(h, w) > max_dim:

        scale_img = max_dim / max(h, w)

        new_w = int(w * scale_img)
        new_h = int(h * scale_img)

        img_np = cv2.resize(
            img_np,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

        h, w = new_h, new_w
        resized = True

    return img_np, h, w, scale_img, resized