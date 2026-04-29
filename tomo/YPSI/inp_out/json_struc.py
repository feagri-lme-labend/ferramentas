def build_section(
    escala,
    p1_id,
    p2_id,
    dist_real,
    origin_x,
    origin_y,
    side_cm,
    nx,
    ny,
    resolution_cm,
    pontos_cm,
    transducers,
    propagation_paths
):

    return {
        "section_id": None,
        "height_cm": None,
        "acquisition_time": None,

        "calibration": {
            "scale_cm_per_pixel": escala,
            "reference_points": {
                "p1_id": int(p1_id),
                "p2_id": int(p2_id)
            },
            "real_distance": float(dist_real)
        },

        "domain": {
            "type": "cartesian",

            "centroid_cm": {
                "x": 0.0,
                "y": 0.0
            },

            "grid_origin_cm": {
                "x": round(origin_x, 3),
                "y": round(origin_y, 3)
            },

            "size": {
                "width_cm": round(side_cm, 10),
                "height_cm": round(side_cm, 10)
            },

            "grid": {
                "nx": nx,
                "ny": ny,
                "resolution_cm": round(resolution_cm, 5)
            }
        },

        "metadata": {
            "length_unit": "centimeter",
            "time_unit": "microsecond",
            "symmetry": True
        },

        "contour_nodes": [
            {
                "id": i + 1,
                "x": round(p[0], 10),
                "y": round(p[1], 10)
            }
            for i, p in enumerate(pontos_cm)
        ],

        "transducers": transducers,

        "propagation_paths": propagation_paths
    }