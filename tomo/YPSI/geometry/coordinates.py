def convert_points_to_cm(pontos, centro, escala):

    pontos_cm = []

    for px, py in pontos:

        x_cm = (px - centro[0]) * escala
        y_cm = -(py - centro[1]) * escala

        pontos_cm.append([x_cm, y_cm])

    return pontos_cm