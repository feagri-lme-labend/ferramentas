import io
import json
import zipfile

from core.experiment_state import build_experiment_state
from utils.utils import write_png_to_zip


def build_export_zip(
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
    session_state,
    img_np,
    binary,
    binary_grid,
    img_poly_rgb,
    result_rgb,
    json_str
):

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zf:

        experiment_state = build_experiment_state(
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
        )

        experiment_state["images"] = {}

        experiment_state["images"]["raw_image"] = write_png_to_zip(
            zf, img_np, "0_RAW_IMAGE.png"
        )

        experiment_state["images"]["threshold_real"] = write_png_to_zip(
            zf, binary, "1_THRESHOLD_REAL.png"
        )

        experiment_state["images"]["threshold_grid"] = write_png_to_zip(
            zf, binary_grid, "2_THRESHOLD_GRID.png"
        )

        experiment_state["images"]["mesh"] = write_png_to_zip(
            zf, img_poly_rgb, "3_MESH.png"
        )

        experiment_state["images"]["cropped"] = write_png_to_zip(
            zf, result_rgb, "4_CROPPED_SECTION.png"
        )

        experiment_json = json.dumps(experiment_state, indent=2)

        zf.writestr("5_EXPERIMENT_STATE.json", experiment_json)

        zf.writestr("6_YPSII_INPUT.json", json_str)

    return zip_buffer