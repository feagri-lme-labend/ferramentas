import numpy as np


def compute_scale(pontos, p1_id, p2_id, dist_real):

    p1 = pontos[p1_id - 1]
    p2 = pontos[p2_id - 1]

    dist_pixels = np.linalg.norm(p1 - p2)

    escala = dist_real / dist_pixels if dist_pixels > 0 else 0

    return escala