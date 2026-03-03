import numpy as np
import plotly.graph_objects as go
from math import cos, sin, pi

# =================================================================
# 1. CONSTANTES DE COR PADRÃO
# =================================================================
# A cor padrão é VERMELHO, conforme sua última instrução.
COLOR_UNIFORM = 'red' 

# =================================================================
# 2. FUNÇÃO DE CÁLCULO DA GEOMETRIA DO POLIEDRO
# =================================================================

def calculate_polyhedron_geometry(L_menor, H_tronco, H_prisma, base_color=COLOR_UNIFORM):
    """
    Calcula os vértices, faces, arestas e dimensões-chave do poliedro (Tronco-Prisma-Tronco).

    Retorna:
    V_mesh (np.array): Vértices para o Plotly Mesh3d (incluindo centros).
    V_points (np.array): Vértices físicos para Scatter3d (pontos).
    F (np.array): Índices de faces triangulares.
    face_colors (list): Lista de cores por face triangular.
    edge_x, edge_y, edge_z (list): Coordenadas para desenhar as arestas.
    poly_dims (dict): Dicionário com R_menor, R_maior e Z4.
    """
    
    L_maior = H_prisma
    
    def R_octogono(L):
        return L / (2 * sin(pi / 8))

    R_menor = R_octogono(L_menor)
    R_maior = R_octogono(L_maior)

    Z1 = 0.0
    Z2 = H_tronco
    Z3 = H_tronco + H_prisma
    Z4 = 2 * H_tronco + H_prisma

    # 1. Geração dos 32 Vértices principais (V0 a V31)
    vertices_list = []
    
    def generate_octagon_ring(R, Z):
        ring_vertices = []
        for i in range(8):
            phi = pi / 8 + i * pi / 4
            x = R * cos(phi)
            y = R * sin(phi)
            ring_vertices.append([x, y, Z])
        return ring_vertices

    vertices_list.extend(generate_octagon_ring(R_menor, Z1))
    vertices_list.extend(generate_octagon_ring(R_maior, Z2))
    vertices_list.extend(generate_octagon_ring(R_maior, Z3))
    vertices_list.extend(generate_octagon_ring(R_menor, Z4))

    V_points = np.array(vertices_list)

    # 2. Adiciona Centros para Triangulação das Bases (Mesh3d)
    vertices_for_mesh_list = list(vertices_list)
    center_idx_base = len(vertices_for_mesh_list)
    vertices_for_mesh_list.append([0.0, 0.0, Z1]) 
    center_idx_top = len(vertices_for_mesh_list)
    vertices_for_mesh_list.append([0.0, 0.0, Z4]) 
    V_mesh = np.array(vertices_for_mesh_list)

    # 3. Definição das Faces (Triangulação)
    faces_tri = []
    face_colors = []
    
    def add_quad(idx1, idx2, idx3, idx4, color):
        faces_tri.append([idx1, idx2, idx3])
        face_colors.append(color)
        faces_tri.append([idx1, idx3, idx4])
        face_colors.append(color)
    
    # (A) Faces Octogonais
    for i in range(8):
        faces_tri.append([center_idx_base, i, (i + 1) % 8])
        face_colors.append(base_color)
    for i in range(8):
        faces_tri.append([center_idx_top, 24 + i, 24 + (i + 1) % 8])
        face_colors.append(base_color)
        
    # (B) Faces Laterais
    for i in range(8):
        # Tronco Inferior
        v1 = i; v2 = i + 8; v3 = (i + 1) % 8 + 8; v4 = (i + 1) % 8
        add_quad(v1, v2, v3, v4, base_color)
        
        # Prisma Central
        v1 = i + 8; v2 = i + 16; v3 = (i + 1) % 8 + 16; v4 = (i + 1) % 8 + 8
        add_quad(v1, v2, v3, v4, base_color)
        
        # Tronco Superior
        v1 = i + 16; v2 = i + 24; v3 = (i + 1) % 8 + 24; v4 = (i + 1) % 8 + 16
        add_quad(v1, v2, v3, v4, base_color)

    F = np.array(faces_tri).T

    # 4. Geração das Arestas para o Plotly Scatter3d (linhas)
    edge_x = []; edge_y = []; edge_z = []
    for k in range(4): 
        start_idx = k * 8
        for i in range(8):
            v_curr = V_points[start_idx + i]; v_next = V_points[start_idx + (i + 1) % 8]
            edge_x.extend([v_curr[0], v_next[0], None]); edge_y.extend([v_curr[1], v_next[1], None]); edge_z.extend([v_curr[2], v_next[2], None])

    for i in range(8):
        v_upper = V_points[8 + i]; v_lower = V_points[i]
        edge_x.extend([v_lower[0], v_upper[0], None]); edge_y.extend([v_lower[1], v_upper[1], None]); edge_z.extend([v_lower[2], v_upper[2], None])
        v_upper = V_points[16 + i]; v_lower = V_points[8 + i]
        edge_x.extend([v_lower[0], v_upper[0], None]); edge_y.extend([v_lower[1], v_upper[1], None]); edge_z.extend([v_lower[2], v_upper[2], None])
        v_upper = V_points[24 + i]; v_lower = V_points[16 + i]
        edge_x.extend([v_lower[0], v_upper[0], None]); edge_y.extend([v_lower[1], v_upper[1], None]); edge_z.extend([v_lower[2], v_upper[2], None])
    
    poly_dims = {
        "R_menor": R_menor,
        "R_maior": R_maior,
        "Z4": Z4
    }

    return V_mesh, V_points, F, face_colors, edge_x, edge_y, edge_z, poly_dims


# =================================================================
# 3. FUNÇÃO DE GERAÇÃO DA FIGURA PLOTLY
# =================================================================

def create_polyhedron_figure(L_menor, H_tronco, H_prisma, base_color='red'):
    """
    Gera e retorna a figura Plotly 3D completa do poliedro.
    """
    
    V_mesh, V_points, F, colors, edge_x, edge_y, edge_z, poly_dims = calculate_polyhedron_geometry(
        L_menor=L_menor, 
        H_tronco=H_tronco, 
        H_prisma=H_prisma,
        base_color=base_color
    )

    x_mesh, y_mesh, z_mesh = V_mesh[:, 0], V_mesh[:, 1], V_mesh[:, 2]
    x_points, y_points, z_points = V_points[:, 0], V_points[:, 1], V_points[:, 2]

    fig = go.Figure(data=[
        # Trace 1: O corpo do poliedro
        go.Mesh3d(
            x=x_mesh, y=y_mesh, z=z_mesh,
            i=F[0], j=F[1], k=F[2],
            facecolor=colors,
            opacity=0.9,
            flatshading=True,
            hoverinfo='skip',
            name='Corpo do Poliedro'
        ),
        # Trace 2: As arestas (linhas pretas)
        go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='black', width=4),
            hoverinfo='skip',
            name='Arestas'
        ),
        # Trace 3: Os vértices (pontos pretos)
        go.Scatter3d(
            x=x_points, y=y_points, z=z_points,
            mode='markers',
            marker=dict(
                size=4,
                color='black',
                symbol='circle'
            ),
            hoverinfo='text',
            text=[f"Vértice {i}: ({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})" for i, v in enumerate(V_points)],
            name='Vértices'
        )
    ])

    # 4. Configurações de layout
    min_val_x = V_points[:, 0].min()
    max_val_x = V_points[:, 0].max()
    min_val_y = V_points[:, 1].min()
    max_val_y = V_points[:, 1].max()
    min_val_z = V_points[:, 2].min()
    max_val_z = V_points[:, 2].max()

    padding = max((max_val_x - min_val_x), (max_val_y - min_val_y), (max_val_z - min_val_z)) * 0.1

    fig.update_layout(
        #title='Visualização 3D do Poliedro (Plotly)',
        scene=dict(
            aspectmode='data', 
            xaxis=dict(range=[min_val_x - padding, max_val_x + padding]),
            yaxis=dict(range=[min_val_y - padding, max_val_y + padding]),
            zaxis=dict(range=[min_val_z - padding, max_val_z + padding]),
            xaxis_showgrid=False, yaxis_showgrid=False, zaxis_showgrid=False,
            xaxis_title='', yaxis_title='', zaxis_title='',
            xaxis_visible=False, yaxis_visible=False, zaxis_visible=False
        ),
        height=700,
        showlegend=False
    )
    
    # Retorna a figura Plotly e as dimensões calculadas
    return fig, poly_dims