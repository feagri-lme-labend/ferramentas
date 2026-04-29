from datetime import datetime


def build_experiment_state(
    img_name,
    centro,
    pontos,
    pontos_cm,
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
    transducers,
    propagation_paths,
    session_state
):

    experiment_state = {

        "app": {
            "name": "YPS I",
            "version": "1.0",
            "timestamp": datetime.now().isoformat()
        },

        "section_id": None,
        "height_cm": None,
        "acquisition_time": None,

        "image": {
            "name": img_name,
            "resize_applied": session_state.get("resize_applied"),
            "scale_img": session_state.get("scale_img")
        },

        "geometry": {
            "n_points": session_state.get("n_pontos"),

            "centroid_px": {
                "x": round(float(centro[0]), 3),
                "y": round(float(centro[1]), 3)
            },

            "centroid_cm": {
                "x": 0.0,
                "y": 0.0
            },

            "grid_origin_cm": {
                "x": round(origin_x, 3),
                "y": round(origin_y, 3)
            },

            "polygon_points_px": [
                {"id": i + 1, "x": int(p[0]), "y": int(p[1])}
                for i, p in enumerate(pontos)
            ],

            "polygon_points_cm": [
                {"id": i + 1, "x": round(p[0], 10), "y": round(p[1], 10)}
                for i, p in enumerate(pontos_cm)
            ],
        },

        "style": {
            "line_color": session_state.get("cor_linha"),
            "line_thickness": session_state.get("espessura_linha"),
            "node_radius": session_state.get("raio_ponto"),
            "font_scale": session_state.get("font_scale"),
            "font_thickness": session_state.get("font_thickness")
        },

        "point_settings": {
            "window_size": session_state.get("zoom_size"),
            "zoom_scale": session_state.get("zoom_scale")
        },

        "calibration": {
            "scale_cm_per_pixel": escala,
            "reference_points": {
                "p1_id": int(p1_id),
                "p2_id": int(p2_id)
            },
            "distance_cm": float(dist_real)
        },

        "transducers": transducers,

        "segmentation": {
            "blur_kernel": session_state.get("blur_size"),
            "blur_sigma": session_state.get("blur_sigma"),
            "threshold": session_state.get("threshold")
        },

        "propagation_paths": propagation_paths,

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
        }
    }

    return experiment_state