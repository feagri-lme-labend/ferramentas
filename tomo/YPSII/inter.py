import numpy as np
from scipy.interpolate import Rbf

def du_interpolation_simple(coords, T, grid_x, grid_y, eccentricity=1.05):
    """Modelo Du & Wang Clássico (Elipse sem compensação de distância)"""
    X, Y = np.meshgrid(grid_x, grid_y)
    vel_sum = np.zeros_like(X)
    weight_sum = np.zeros_like(X)
    num_sensors = len(coords)

    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            t_ij = T[i, j]
            if t_ij <= 0: continue
            
            p1, p2 = coords[i], coords[j]
            dist_ij = np.linalg.norm(p1 - p2)
            v_ij = dist_ij / t_ij
            
            d1 = np.sqrt((X - p1[0])**2 + (Y - p1[1])**2)
            d2 = np.sqrt((X - p2[0])**2 + (Y - p2[1])**2)
            dist_total = d1 + d2
            
            mask = dist_total <= (dist_ij * eccentricity)
            if not np.any(mask): continue

            sigma = 0.01 * dist_ij
            weight = np.exp(-((dist_total - dist_ij)**2) / sigma)
            
            vel_sum[mask] += v_ij * weight[mask]
            weight_sum[mask] += weight[mask]

    return X, Y, np.divide(vel_sum, weight_sum, out=np.zeros_like(vel_sum), where=weight_sum != 0)

def du_interpolation_compensated(coords, T, grid_x, grid_y, eccentricity=1.05, compensation_factor=2.0):
    """Modelo Du & Wang Avançado (Elipse com compensação radial)"""
    X, Y = np.meshgrid(grid_x, grid_y)
    vel_sum = np.zeros_like(X)
    weight_sum = np.zeros_like(X)
    num_sensors = len(coords)

    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            t_ij = T[i, j]
            if t_ij <= 0: continue
            
            p1, p2 = coords[i], coords[j]
            dist_ij = np.linalg.norm(p1 - p2)
            v_ij = dist_ij / t_ij
            
            d1 = np.sqrt((X - p1[0])**2 + (Y - p1[1])**2)
            d2 = np.sqrt((X - p2[0])**2 + (Y - p2[1])**2)
            dist_total = d1 + d2
            
            mask = dist_total <= (dist_ij * eccentricity)
            
            sigma = 0.01 * dist_ij
            weight_proximity = np.exp(-((dist_total - dist_ij)**2) / sigma)
            dist_compensation = 1.0 / (dist_ij ** (1 / compensation_factor))
            
            final_weight = weight_proximity * dist_compensation
            
            vel_sum[mask] += v_ij * final_weight[mask]
            weight_sum[mask] += final_weight[mask]

    return X, Y, np.divide(vel_sum, weight_sum, out=np.zeros_like(vel_sum), where=weight_sum != 0)

def linear_back_projection(coords, T, grid_x, grid_y, tolerance=0.01):
    """Modelo LBP (Linear Back-Projection) - Projeção em raios retos"""
    X, Y = np.meshgrid(grid_x, grid_y)
    vel_sum = np.zeros_like(X)
    weight_sum = np.zeros_like(X)
    num_sensors = len(coords)

    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            t_ij = T[i, j]
            if t_ij <= 0: continue
            
            p1, p2 = coords[i], coords[j]
            dist_ij = np.linalg.norm(p1 - p2)
            v_ij = dist_ij / t_ij
            
            # Vetor do raio e projeção escalar para distância ponto-segmento
            v = p2 - p1
            v_norm_sq = np.dot(v, v)
            u = np.clip(((X - p1[0]) * v[0] + (Y - p1[1]) * v[1]) / v_norm_sq, 0, 1)
            
            prox_x, prox_y = p1[0] + u * v[0], p1[1] + u * v[1]
            dist_to_segment = np.sqrt((X - prox_x)**2 + (Y - prox_y)**2)
            
            ray_mask = dist_to_segment <= tolerance
            vel_sum[ray_mask] += v_ij
            weight_sum[ray_mask] += 1

    return X, Y, np.divide(vel_sum, weight_sum, out=np.zeros_like(vel_sum), where=weight_sum != 0)


def art_reconstruction(coords, T, grid_x, grid_y, iterations=5, relaxation=0.1, tolerance=0.02):
    """
    Versão simplificada do ART (Algebraic Reconstruction Technique).
    - iterations: quantas vezes o algoritmo refina o mapa.
    - relaxation: quão agressivo é o ajuste (0.1 a 0.5).
    - tolerance: largura do raio para cálculo de interseção.
    """
    X, Y = np.meshgrid(grid_x, grid_y)
    num_sensors = len(coords)
    
    # 1. Chute inicial: Velocidade média global em todos os pixels
    all_times = []
    all_dists = []
    rays = []

    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            if T[i, j] > 0:
                dist = np.linalg.norm(coords[i] - coords[j])
                all_times.append(T[i, j])
                all_dists.append(dist)
                rays.append(((coords[i], coords[j]), dist, T[i, j]))

    v_avg = np.sum(all_dists) / np.sum(all_times)
    # Trabalhamos com lentidão (slowness = 1/v) para facilitar a soma linear
    slowness = np.full(X.shape, 1.0 / v_avg)

    # Pre-calculamos as máscaras de cada raio para ganhar velocidade
    ray_data = []
    for (p1, p2), dist_ij, t_obs in rays:
        v = p2 - p1
        v_norm_sq = np.dot(v, v)
        u = np.clip(((X - p1[0]) * v[0] + (Y - p1[1]) * v[1]) / v_norm_sq, 0, 1)
        prox_x, prox_y = p1[0] + u * v[0], p1[1] + u * v[1]
        dist_to_seg = np.sqrt((X - prox_x)**2 + (Y - prox_y)**2)
        mask = dist_to_seg <= tolerance
        num_pixels = np.count_nonzero(mask)
        if num_pixels > 0:
            # Comprimento efetivo do raio dentro de cada pixel (simplificado)
            L_ij = dist_ij / num_pixels 
            ray_data.append((mask, t_obs, L_ij, num_pixels))

    # 2. Processo Iterativo
    for _ in range(iterations):
        for mask, t_obs, L_ij, num_pixels in ray_data:
            # Tempo calculado com o mapa atual: t = soma(distancia_pixel * lentidao_pixel)
            t_calc = np.sum(slowness[mask] * L_ij)
            
            # Diferença entre o real e o calculado
            error = t_obs - t_calc
            
            # Ajuste (Back-projection do erro)
            # Delta lentidão = (erro / pixels) * fator de relaxação
            adjustment = (error / (num_pixels * L_ij)) * relaxation
            slowness[mask] += adjustment

    # Converter de volta para velocidade (V = 1/S) e limpar valores irreais
    v_field = 1.0 / slowness
    v_field = np.clip(v_field, 100, 4000) # Limites físicos da madeira
    
    return X, Y, v_field

def rbf_interpolation(coords, T, grid_x, grid_y):
    """
    Interpolação por Funções de Base Radial (RBF).
    Mapeia as velocidades médias dos raios para a grade.
    """
    num_sensors = len(coords)
    obs_x, obs_y, obs_v = [], [], []

    # Gerar pontos de amostragem nos centros dos raios
    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            if T[i, j] > 0:
                p1, p2 = coords[i], coords[j]
                dist = np.linalg.norm(p1 - p2)
                v = dist / T[i, j]
                
                mid_p = (p1 + p2) / 2
                obs_x.append(mid_p[0])
                obs_y.append(mid_p[1])
                obs_v.append(v)

    if not obs_v:
        X, Y = np.meshgrid(grid_x, grid_y)
        return X, Y, np.zeros_like(X)

    # Criar o interpolador RBF
    # 'multiquadric' ou 'thin_plate' são ótimos para madeira
    rbf = Rbf(obs_x, obs_y, obs_v, function='multiquadric', smooth=0.1)
    
    X, Y = np.meshgrid(grid_x, grid_y)
    v_field = rbf(X, Y)
    
    return X, Y, v_field

def ebsi_interpolation(coords, T, grid_x, grid_y, eccentricity=1.1):
    """
    EBSI Clássico (Ellipse-Based Spatial Interpolation)
    O modelo que o artigo cita como base de comparação.
    Interpola pontos da grade baseando-se na proximidade elíptica dos raios.
    """
    X, Y = np.meshgrid(grid_x, grid_y)
    v_field = np.zeros_like(X)
    w_sum = np.zeros_like(X)
    num_sensors = len(coords)

    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            if T[i, j] <= 0: continue
            p1, p2 = coords[i], coords[j]
            dist_ij = np.linalg.norm(p1 - p2)
            v_ij = dist_ij / T[i, j]
            
            # Geometria da elipse
            a = (dist_ij * eccentricity) / 2.0
            d1 = np.sqrt((X - p1[0])**2 + (Y - p1[1])**2)
            d2 = np.sqrt((X - p2[0])**2 + (Y - p2[1])**2)
            mask = (d1 + d2) <= (2 * a)
            
            # Ponderação linear simples dentro da elipse
            weight = (2 * a - (d1 + d2)) / (2 * a - dist_ij)
            weight[~mask] = 0
            
            v_field += v_ij * weight
            w_sum += weight

    return X, Y, np.divide(v_field, w_sum, out=np.zeros_like(v_field), where=w_sum != 0)

def du_2018_segmented_rays(coords, T, grid_x, grid_y, eccentricity=1.05, n_segments=10):
    """
    MODELO PROPOSTO POR DU (2018)
    Baseado em Raios de Propagação Segmentados.
    """
    X, Y = np.meshgrid(grid_x, grid_y)
    num_sensors = len(coords)
    
    # 1. Gerar os Raios Originais
    original_rays = []
    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            if T[i, j] > 0:
                p1, p2 = coords[i], coords[j]
                d = np.linalg.norm(p1 - p2)
                original_rays.append({'p1': p1, 'p2': p2, 'v': d/T[i, j], 'dist': d})

    # 2. Segmentar cada raio e estimar a velocidade do segmento
    # Segundo o artigo, a velocidade de cada segmento é a média ponderada 
    # dos raios originais que cruzam sua vizinhança elíptica.
    segmented_data_x = []
    segmented_data_y = []
    segmented_data_v = []

    for ray in original_rays:
        # Divide o raio em N pontos (segmentos)
        for t in np.linspace(0.1, 0.9, n_segments):
            seg_p = ray['p1'] + t * (ray['p2'] - ray['p1'])
            
            # Para este ponto do segmento, calcula a influência de outros raios
            v_seg = 0
            w_seg = 0
            for other in original_rays:
                # Distância do ponto do segmento aos focos do outro raio
                d1 = np.linalg.norm(seg_p - other['p1'])
                d2 = np.linalg.norm(seg_p - other['p2'])
                a = (other['dist'] * eccentricity) / 2.0
                
                if (d1 + d2) <= (2 * a):
                    w = (2 * a - (d1 + d2)) / (2 * a - other['dist'])
                    v_seg += other['v'] * w
                    w_seg += w
            
            if w_seg > 0:
                segmented_data_x.append(seg_p[0])
                segmented_data_y.append(seg_p[1])
                segmented_data_v.append(v_seg / w_seg)

    # 3. Interpolação final da grade usando os segmentos como novas fontes de dados
    # (Aqui usamos uma interpolação IDW sobre os segmentos para preencher a grade)
    v_field = np.zeros_like(X)
    w_field = np.zeros_like(X)
    
    pts_x = np.array(segmented_data_x)
    pts_y = np.array(segmented_data_y)
    pts_v = np.array(segmented_data_v)
    
    for i in range(len(pts_v)):
        dist_sq = (X - pts_x[i])**2 + (Y - pts_y[i])**2
        w = 1.0 / (dist_sq + 1e-6) # Distância inversa
        v_field += pts_v[i] * w
        w_field += w

    return X, Y, np.divide(v_field, w_field, out=np.zeros_like(v_field), where=w_field != 0)

def sirt_reconstruction(coords, T, grid_x, grid_y, iterations=10, relaxation=0.1, ray_width=0.02):
    """
    SIRT - Simultaneous Iterative Reconstruction Technique.
    Resolve a integral da lentidão: T = integral(s * dl)
    """
    res_x, res_y = len(grid_x), len(grid_y)
    X, Y = np.meshgrid(grid_x, grid_y)
    
    # 1. Inicializar campo de lentidão (s = 1/v) com a média dos raios
    num_sensors = len(coords)
    v_amostras = []
    raios = []
    
    for i in range(num_sensors):
        for j in range(i + 1, num_sensors):
            if T[i, j] > 0:
                dist = np.linalg.norm(coords[i] - coords[j])
                v_amostras.append(dist / T[i, j])
                raios.append({'p1': coords[i], 'p2': coords[j], 'time': T[i, j], 'dist': dist})

    v_media = np.mean(v_amostras) if v_amostras else 1000.0
    s_field = np.full((res_y, res_x), 1.0 / v_media)
    
    # Pré-calcular as distâncias de cada pixel aos raios (Matriz de pesos)
    # Para SIRT, o peso é o comprimento do caminho (dl) do raio dentro do pixel
    # Aqui usamos uma aproximação Gaussiana de largura de raio para estabilidade
    pixel_size = abs(grid_x[1] - grid_x[0])
    
    for _ in range(iterations):
        delta_s_total = np.zeros_like(s_field)
        count_map = np.zeros_like(s_field)
        
        for raio in raios:
            p1, p2 = raio['p1'], raio['p2']
            
            # Vetor do raio
            v = p2 - p1
            v_mag_sq = np.dot(v, v)
            
            # Calcular distância de todos os pontos da grade ao segmento do raio
            u = ((X - p1[0]) * v[0] + (Y - p1[1]) * v[1]) / v_mag_sq
            u = np.clip(u, 0, 1)
            
            dist_sq = (p1[0] + u * v[0] - X)**2 + (p1[1] + u * v[1] - Y)**2
            
            # Máscara dos pixels influenciados pelo raio
            mask = dist_sq < (ray_width**2)
            
            if not np.any(mask): continue
            
            # Estimativa do tempo atual (Integral s * dl)
            # Aproximamos dl pelo tamanho do pixel onde o raio passa
            current_time_est = np.sum(s_field[mask]) * (raio['dist'] / np.count_nonzero(mask))
            
            # Erro de tempo
            error = raio['time'] - current_time_est
            
            # Correção de lentidão proporcional (distribuída pelos pixels do raio)
            # SIRT: Acumula as correções para aplicar a média no final da iteração
            delta_s = error / raio['dist']
            delta_s_total[mask] += delta_s
            count_map[mask] += 1
            
        # Atualização simultânea (Simultaneous)
        update_mask = count_map > 0
        s_field[update_mask] += relaxation * (delta_s_total[update_mask] / count_map[update_mask])
        
        # Garantir que a lentidão não seja negativa ou absurda (v > 100m/s)
        s_field = np.clip(s_field, 1/4000, 1/100)

    v_field = 1.0 / s_field
    return X, Y, v_field