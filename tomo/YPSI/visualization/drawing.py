import cv2
import numpy as np


def draw_polygon_mesh(
    img_np,
    pontos,
    transducers,
    idx,
    centro,
    cor_linha,
    espessura_linha,
    raio_ponto,
    font_scale,
    font_thickness
):

    pts = np.array([pontos], dtype=np.int32)

    img_poly = img_np.copy()

    # -------------------
    # POLYGON
    # -------------------

    cv2.polylines(img_poly, pts, True, cor_linha, espessura_linha)

    # -------------------
    # CENTROID
    # -------------------

    cx, cy = int(centro[0]), int(centro[1])

    cv2.line(img_poly, (cx-20, cy), (cx+20, cy), (0,255,0), 2)
    cv2.line(img_poly, (cx, cy-20), (cx, cy+20), (0,255,0), 2)

    cv2.circle(img_poly, (cx, cy), 5, (255,0,0), -1)

    cv2.putText(
        img_poly,
        "C",
        (cx+10, cy-10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0,255,0),
        2,
        cv2.LINE_AA
    )

    # -------------------
    # NODES + SENSORS
    # -------------------

    for i, (px, py) in enumerate(pontos):

        px, py = int(px), int(py)

        is_sensor = None
        for s in transducers:
            if s["contour_node_id"] == i+1:
                is_sensor = s
                break

        if is_sensor is None:

            cv2.circle(img_poly, (px, py), raio_ponto, (255,255,255), -1)
            cv2.circle(img_poly, (px, py), raio_ponto, (0,0,0), 2)

        else:

            cv2.circle(img_poly, (px, py), raio_ponto + 5, (0,255,255), 2)
            cv2.circle(img_poly, (px, py), raio_ponto, (255,255,0), -1)

        if i == idx:
            cv2.circle(img_poly, (px, py), raio_ponto + 15, (0,255,0), 4)

        text = str(i+1)
        font = cv2.FONT_HERSHEY_SIMPLEX

        (tw, th), _ = cv2.getTextSize(
            text,
            font,
            font_scale,
            font_thickness
        )

        cv2.putText(
            img_poly,
            text,
            (px - tw//2, py + th//2),
            font,
            font_scale,
            (0,0,0),
            font_thickness,
            cv2.LINE_AA
        )

        if is_sensor is not None:

            sid = is_sensor["id"]

            cv2.putText(
                img_poly,
                f"T{sid}",
                (px + 15, py - 15),
                font,
                0.6,
                (0,255,255),
                2,
                cv2.LINE_AA
            )

    # -------------------
    # SENSOR CONNECTIONS
    # -------------------

    sensor_points = []

    for s in transducers:

        node_id = s["contour_node_id"] - 1

        px, py = pontos[node_id]

        sensor_points.append((int(px), int(py)))

    for i in range(len(sensor_points)):

        for j in range(i+1, len(sensor_points)):

            cv2.line(
                img_poly,
                sensor_points[i],
                sensor_points[j],
                (0,0,0),
                1,
                cv2.LINE_AA
            )

    return img_poly