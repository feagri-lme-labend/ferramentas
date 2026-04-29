import numpy as np


def compute_grid_domain(pontos_cm, nx, ny):
    """
    Compute grid origin, size and resolution from contour points in cm.
    """

    xs = [p[0] for p in pontos_cm]
    ys = [p[1] for p in pontos_cm]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width_cm = max_x - min_x
    height_cm = max_y - min_y

    side_cm = max(width_cm, height_cm)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    origin_x = cx - side_cm / 2
    origin_y = cy - side_cm / 2

    resolution_cm = side_cm / nx

    return {
        "origin_x": origin_x,
        "origin_y": origin_y,
        "side_cm": side_cm,
        "resolution_cm": resolution_cm,
        "nx": nx,
        "ny": ny
    }


def build_binary_grid(
    binary,
    escala,
    centro,
    origin_x,
    origin_y,
    resolution_cm,
    nx,
    ny,
    w,
    h
):
    """
    Convert pixel segmentation to tomographic grid (vectorized version).
    Much faster for large grids.
    """

    binary_grid = np.zeros((ny, nx), dtype=np.uint8)

    if escala == 0:
        return binary_grid

    cx, cy = centro

    # grid indices
    j = np.arange(nx)
    i = np.arange(ny)

    J, I = np.meshgrid(j, i)

    # same equations you used
    curr_x_cm = origin_x + (J * resolution_cm)
    curr_y_cm = origin_y + ((ny - 1 - I) * resolution_cm)

    val_x = (curr_x_cm / escala) + cx
    val_y = cy - (curr_y_cm / escala)

    px = np.round(val_x).astype(int)
    py = np.round(val_y).astype(int)

    valid = (
        (px >= 0) &
        (px < w) &
        (py >= 0) &
        (py < h)
    )

    binary_grid[valid] = binary[py[valid], px[valid]]

    return binary_grid