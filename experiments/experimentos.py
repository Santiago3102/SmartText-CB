"""
experimentos.py — SmartText
Módulo de experimentación y comparación de parámetros.

Experimentos:
    1. Levenshtein  — umbral de distancia vs candidatos encontrados y tiempo
    2. Lógica difusa — funciones de membresía triangular vs trapezoidal
    3. SOM          — tamaño de grid vs error de cuantización y tiempo
    4. N-gramas     — bigramas vs trigramas en precisión de sugerencia

Salidas:
    - experimento_levenshtein.png
    - experimento_fuzzy.png
    - experimento_som.png
    - experimento_ngramas.png
    - resumen_resultados.txt
"""

import os
import sys
import time
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import Counter

# Estilo visual consistente
plt.rcParams.update({
    'figure.facecolor': '#0F0F14',
    'axes.facecolor':   '#1A1A24',
    'axes.edgecolor':   '#2A2A3A',
    'axes.labelcolor':  '#F0EEFF',
    'text.color':       '#F0EEFF',
    'xtick.color':      '#7A7A9A',
    'ytick.color':      '#7A7A9A',
    'grid.color':       '#2A2A3A',
    'grid.linestyle':   '--',
    'grid.alpha':       0.5,
    'font.size':        11,
    'axes.titlesize':   13,
    'axes.titleweight': 'bold',
    'lines.linewidth':  2,
})

COLORES = ['#7B61FF', '#00D4AA', '#FFB347', '#FF6B6B', '#4FC3F7']
SALIDA  = os.path.dirname(__file__)


# ── Utilidad: barra de progreso simple ──────────────────────────────────────

def progreso(actual, total, label=''):
    pct  = int(actual / total * 40)
    barra = '█' * pct + '░' * (40 - pct)
    print(f'\r  [{barra}] {actual}/{total} {label}', end='', flush=True)
    if actual == total:
        print()


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENTO 1 — Levenshtein: umbral vs candidatos y tiempo
# ═══════════════════════════════════════════════════════════════════════════

def experimento_levenshtein(vocabulario, n_palabras_test=50):
    print('\n[1/4] Experimento Levenshtein...')

    from levenshtein import buscar_candidatos, distancia_levenshtein

    # Palabras de prueba con errores tipográficos simulados
    palabras_base = list(vocabulario)[:n_palabras_test]
    errores = []
    for p in palabras_base:
        if len(p) > 3:
            # Introducir error: intercambiar dos caracteres
            lst = list(p)
            lst[1], lst[2] = lst[2], lst[1]
            errores.append(''.join(lst))

    umbrales      = [1, 2, 3]
    tiempos_media = []
    candidatos_media = []
    precision_media  = []

    for i, umbral in enumerate(umbrales):
        progreso(i+1, len(umbrales), f'umbral={umbral}')
        tiempos = []
        n_cands = []
        aciertos = []

        for error, original in zip(errores[:30], palabras_base[:30]):
            t0 = time.perf_counter()
            cands = buscar_candidatos(error, vocabulario,
                                      max_distancia=umbral, top_n=10)
            t1 = time.perf_counter()
            tiempos.append((t1 - t0) * 1000)
            n_cands.append(len(cands))
            # Precisión: ¿está la palabra original en los candidatos?
            acierto = any(c[0] == original for c in cands)
            aciertos.append(int(acierto))

        tiempos_media.append(np.mean(tiempos))
        candidatos_media.append(np.mean(n_cands))
        precision_media.append(np.mean(aciertos) * 100)

    # Gráfica
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Experimento 1 — Distancia de Levenshtein\nImpacto del umbral máximo de distancia',
                 fontsize=14, y=1.02)

    ax = axes[0]
    bars = ax.bar(umbrales, tiempos_media, color=COLORES[:3], width=0.5)
    ax.set_title('Tiempo de búsqueda')
    ax.set_xlabel('Umbral máximo (ediciones)')
    ax.set_ylabel('Tiempo promedio (ms)')
    ax.set_xticks(umbrales)
    ax.grid(axis='y')
    for bar, val in zip(bars, tiempos_media):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val:.2f}ms', ha='center', va='bottom', fontsize=10,
                color='#F0EEFF')

    ax = axes[1]
    bars = ax.bar(umbrales, candidatos_media, color=COLORES[:3], width=0.5)
    ax.set_title('Candidatos encontrados')
    ax.set_xlabel('Umbral máximo (ediciones)')
    ax.set_ylabel('Candidatos promedio')
    ax.set_xticks(umbrales)
    ax.grid(axis='y')
    for bar, val in zip(bars, candidatos_media):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{val:.1f}', ha='center', va='bottom', fontsize=10,
                color='#F0EEFF')

    ax = axes[2]
    ax.plot(umbrales, precision_media, 'o-', color=COLORES[0], markersize=10)
    ax.fill_between(umbrales, precision_media, alpha=0.2, color=COLORES[0])
    ax.set_title('Precisión (palabra original recuperada)')
    ax.set_xlabel('Umbral máximo (ediciones)')
    ax.set_ylabel('Precisión (%)')
    ax.set_xticks(umbrales)
    ax.set_ylim(0, 110)
    ax.grid()
    for x, y in zip(umbrales, precision_media):
        ax.annotate(f'{y:.1f}%', (x, y), textcoords='offset points',
                    xytext=(0, 10), ha='center', fontsize=10)

    plt.tight_layout()
    ruta = os.path.join(SALIDA, 'experimento_levenshtein.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#0F0F14')
    plt.close()
    print(f'  → Guardado: {ruta}')

    return {
        'umbrales': umbrales,
        'tiempos_ms': [round(t, 3) for t in tiempos_media],
        'candidatos': [round(c, 2) for c in candidatos_media],
        'precision_pct': [round(p, 2) for p in precision_media],
    }


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENTO 2 — Lógica difusa: triangular vs trapezoidal
# ═══════════════════════════════════════════════════════════════════════════

def experimento_fuzzy():
    print('\n[2/4] Experimento Lógica Difusa...')

    import numpy as np
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl

    universo = np.linspace(0, 1, 100)

    def construir_sistema(tipo='triangular'):
        distancia  = ctrl.Antecedent(universo, 'distancia')
        frecuencia = ctrl.Antecedent(universo, 'frecuencia')
        relevancia = ctrl.Consequent(universo, 'relevancia')

        if tipo == 'triangular':
            distancia['cercana']  = fuzz.trimf(universo, [0.0, 0.0, 0.35])
            distancia['media']    = fuzz.trimf(universo, [0.2, 0.5, 0.8])
            distancia['lejana']   = fuzz.trimf(universo, [0.65, 1.0, 1.0])
            frecuencia['baja']    = fuzz.trimf(universo, [0.0, 0.0, 0.4])
            frecuencia['media']   = fuzz.trimf(universo, [0.25, 0.5, 0.75])
            frecuencia['alta']    = fuzz.trimf(universo, [0.6, 1.0, 1.0])
        else:  # trapezoidal
            distancia['cercana']  = fuzz.trapmf(universo, [0.0, 0.0, 0.2, 0.4])
            distancia['media']    = fuzz.trapmf(universo, [0.2, 0.35, 0.65, 0.8])
            distancia['lejana']   = fuzz.trapmf(universo, [0.6, 0.8, 1.0, 1.0])
            frecuencia['baja']    = fuzz.trapmf(universo, [0.0, 0.0, 0.2, 0.45])
            frecuencia['media']   = fuzz.trapmf(universo, [0.2, 0.35, 0.65, 0.8])
            frecuencia['alta']    = fuzz.trapmf(universo, [0.55, 0.75, 1.0, 1.0])

        relevancia['muy_baja'] = fuzz.trimf(universo, [0.0,  0.0,  0.25])
        relevancia['baja']     = fuzz.trimf(universo, [0.1,  0.25, 0.45])
        relevancia['media']    = fuzz.trimf(universo, [0.3,  0.5,  0.7])
        relevancia['alta']     = fuzz.trimf(universo, [0.55, 0.75, 0.9])
        relevancia['muy_alta'] = fuzz.trimf(universo, [0.75, 1.0,  1.0])

        reglas = [
            ctrl.Rule(distancia['cercana'] & frecuencia['alta'],  relevancia['muy_alta']),
            ctrl.Rule(distancia['cercana'] & frecuencia['media'], relevancia['alta']),
            ctrl.Rule(distancia['cercana'] & frecuencia['baja'],  relevancia['media']),
            ctrl.Rule(distancia['media']   & frecuencia['alta'],  relevancia['alta']),
            ctrl.Rule(distancia['media']   & frecuencia['media'], relevancia['media']),
            ctrl.Rule(distancia['media']   & frecuencia['baja'],  relevancia['baja']),
            ctrl.Rule(distancia['lejana'],                        relevancia['muy_baja']),
        ]
        sistema = ctrl.ControlSystem(reglas)
        return ctrl.ControlSystemSimulation(sistema)

    # Casos de prueba: (distancia, frecuencia, descripcion)
    casos = [
        (0.05, 0.95, 'Óptimo'),
        (0.1,  0.8,  'Muy bueno'),
        (0.2,  0.7,  'Bueno'),
        (0.3,  0.5,  'Moderado'),
        (0.5,  0.4,  'Regular'),
        (0.6,  0.2,  'Malo'),
        (0.8,  0.1,  'Muy malo'),
        (0.95, 0.05, 'Pésimo'),
    ]

    resultados = {'triangular': [], 'trapezoidal': [], 'tiempos': {'triangular': [], 'trapezoidal': []}}

    for tipo in ['triangular', 'trapezoidal']:
        sim = construir_sistema(tipo)
        for dist, freq, _ in casos:
            t0 = time.perf_counter()
            sim.input['distancia']  = dist
            sim.input['frecuencia'] = freq
            try:
                sim.compute()
                val = sim.output['relevancia']
            except Exception:
                val = max(0, (1 - dist) * 0.6 + freq * 0.4)
            t1 = time.perf_counter()
            resultados[tipo].append(val)
            resultados['tiempos'][tipo].append((t1 - t0) * 1000)

    etiquetas = [c[2] for c in casos]
    x = np.arange(len(etiquetas))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Experimento 2 — Sistema de Lógica Difusa\nFunciones de membresía triangular vs trapezoidal',
                 fontsize=14, y=1.02)

    ax = axes[0]
    w = 0.35
    bars1 = ax.bar(x - w/2, resultados['triangular'],  w, label='Triangular',  color=COLORES[0], alpha=0.85)
    bars2 = ax.bar(x + w/2, resultados['trapezoidal'], w, label='Trapezoidal', color=COLORES[1], alpha=0.85)
    ax.set_title('Relevancia por tipo de membresía')
    ax.set_xlabel('Caso de prueba')
    ax.set_ylabel('Relevancia defuzzificada')
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=30, ha='right', fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.legend()
    ax.grid(axis='y')

    ax = axes[1]
    diferencia = [abs(t - tr) for t, tr in
                  zip(resultados['triangular'], resultados['trapezoidal'])]
    ax.plot(etiquetas, resultados['triangular'],  'o-', color=COLORES[0],
            label='Triangular',  markersize=8)
    ax.plot(etiquetas, resultados['trapezoidal'], 's-', color=COLORES[1],
            label='Trapezoidal', markersize=8)
    ax.fill_between(range(len(etiquetas)),
                    resultados['triangular'], resultados['trapezoidal'],
                    alpha=0.15, color=COLORES[2], label='Diferencia')
    ax.set_title('Comparación de curvas de relevancia')
    ax.set_xlabel('Caso de prueba')
    ax.set_ylabel('Relevancia')
    ax.set_xticks(range(len(etiquetas)))
    ax.set_xticklabels(etiquetas, rotation=30, ha='right', fontsize=9)
    ax.legend()
    ax.grid()

    plt.tight_layout()
    ruta = os.path.join(SALIDA, 'experimento_fuzzy.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#0F0F14')
    plt.close()
    print(f'  → Guardado: {ruta}')

    return {
        'casos': etiquetas,
        'triangular': [round(v, 4) for v in resultados['triangular']],
        'trapezoidal': [round(v, 4) for v in resultados['trapezoidal']],
        'diferencia_media': round(np.mean(diferencia), 4),
        'tiempo_triangular_ms': round(np.mean(resultados['tiempos']['triangular']), 4),
        'tiempo_trapezoidal_ms': round(np.mean(resultados['tiempos']['trapezoidal']), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENTO 3 — SOM: tamaño de grid vs error y tiempo
# ═══════════════════════════════════════════════════════════════════════════

def experimento_som(vocabulario, frecuencias):
    print('\n[3/4] Experimento SOM...')

    from som_model import preparar_datos_som, entrenar_som

    palabras, X = preparar_datos_som(vocabulario, frecuencias,
                                      min_freq=5, max_palabras=200)
    print(f'  Datos: {len(palabras)} palabras, vector dim={X.shape[1]}')

    configuraciones = [
        (6,  6,  300),
        (8,  8,  500),
        (10, 10, 700),
        (12, 12, 900),
        (15, 15, 1000),
    ]

    grids       = [f'{gx}×{gy}' for gx, gy, _ in configuraciones]
    errores_q   = []
    errores_top = []
    tiempos_s   = []

    for i, (gx, gy, n_iter) in enumerate(configuraciones):
        progreso(i+1, len(configuraciones), f'grid={gx}x{gy}')
        t0  = time.perf_counter()
        som = entrenar_som(X, grid_x=gx, grid_y=gy, n_iter=n_iter, seed=42)
        t1  = time.perf_counter()

        # Error de cuantización: distancia promedio al BMU
        eq = som.quantization_error(X)
        errores_q.append(eq)

        # Error topográfico: proporción de muestras cuyo 2do BMU no es vecino del 1ro
        et = som.topographic_error(X)
        errores_top.append(et)

        tiempos_s.append(t1 - t0)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Experimento 3 — Self-Organizing Map (SOM)\nImpacto del tamaño de grid en calidad y tiempo',
                 fontsize=14, y=1.02)

    ax = axes[0]
    ax.plot(grids, errores_q, 'o-', color=COLORES[0], markersize=9)
    ax.fill_between(range(len(grids)), errores_q, alpha=0.2, color=COLORES[0])
    ax.set_title('Error de cuantización')
    ax.set_xlabel('Tamaño del grid')
    ax.set_ylabel('Error de cuantización')
    ax.set_xticks(range(len(grids)))
    ax.set_xticklabels(grids)
    ax.grid()
    for i, v in enumerate(errores_q):
        ax.annotate(f'{v:.4f}', (i, v), textcoords='offset points',
                    xytext=(0, 8), ha='center', fontsize=9)

    ax = axes[1]
    ax.plot(grids, errores_top, 's-', color=COLORES[1], markersize=9)
    ax.fill_between(range(len(grids)), errores_top, alpha=0.2, color=COLORES[1])
    ax.set_title('Error topográfico')
    ax.set_xlabel('Tamaño del grid')
    ax.set_ylabel('Error topográfico')
    ax.set_xticks(range(len(grids)))
    ax.set_xticklabels(grids)
    ax.grid()
    for i, v in enumerate(errores_top):
        ax.annotate(f'{v:.3f}', (i, v), textcoords='offset points',
                    xytext=(0, 8), ha='center', fontsize=9)

    ax = axes[2]
    bars = ax.bar(range(len(grids)), tiempos_s, color=COLORES[:len(grids)])
    ax.set_title('Tiempo de entrenamiento')
    ax.set_xlabel('Tamaño del grid')
    ax.set_ylabel('Tiempo (segundos)')
    ax.set_xticks(range(len(grids)))
    ax.set_xticklabels(grids)
    ax.grid(axis='y')
    for bar, val in zip(bars, tiempos_s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}s', ha='center', va='bottom', fontsize=9,
                color='#F0EEFF')

    plt.tight_layout()
    ruta = os.path.join(SALIDA, 'experimento_som.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#0F0F14')
    plt.close()
    print(f'  → Guardado: {ruta}')

    return {
        'grids': grids,
        'error_cuantizacion': [round(e, 5) for e in errores_q],
        'error_topografico':  [round(e, 4) for e in errores_top],
        'tiempos_s':          [round(t, 3) for t in tiempos_s],
        'grid_optimo': grids[errores_q.index(min(errores_q))],
    }


# ═══════════════════════════════════════════════════════════════════════════
# EXPERIMENTO 4 — N-gramas: bigramas vs trigramas
# ═══════════════════════════════════════════════════════════════════════════

def experimento_ngramas():
    print('\n[4/4] Experimento N-gramas...')

    import nltk
    from nltk.corpus import cess_esp
    from nltk.util import ngrams

    nltk.download('cess_esp', quiet=True)
    oraciones = [
        [w.lower() for w in s if w.isalpha()]
        for s in cess_esp.sents()
    ]

    # Construir modelos
    def construir_modelo(n):
        conteos = Counter()
        conteos_base = Counter()
        for oracion in oraciones:
            if len(oracion) < n:
                continue
            grams = list(ngrams(oracion, n))
            for gram in grams:
                conteos[gram] += 1
                conteos_base[gram[:-1]] += 1
        return conteos, conteos_base

    print('  Entrenando bigramas...')
    t0 = time.perf_counter()
    bi_conteos, bi_base = construir_modelo(2)
    t_bi = time.perf_counter() - t0

    print('  Entrenando trigramas...')
    t0 = time.perf_counter()
    tri_conteos, tri_base = construir_modelo(3)
    t_tri = time.perf_counter() - t0

    # Evaluación: dado contexto, predecir siguiente palabra
    # Usar oraciones de prueba (últimas 100)
    oraciones_test = oraciones[-100:]

    def predecir_bigrama(contexto):
        w = contexto[-1]
        cands = {k[1]: v for k, v in bi_conteos.items() if k[0] == w}
        return max(cands, key=cands.get) if cands else None

    def predecir_trigrama(contexto):
        if len(contexto) < 2:
            return predecir_bigrama(contexto)
        w1, w2 = contexto[-2], contexto[-1]
        cands = {k[2]: v for k, v in tri_conteos.items()
                 if k[0] == w1 and k[1] == w2}
        if not cands:
            return predecir_bigrama(contexto)
        return max(cands, key=cands.get)

    aciertos_bi  = []
    aciertos_tri = []
    perp_bi      = []
    perp_tri     = []
    V = len(set(w for o in oraciones for w in o))

    for oracion in oraciones_test:
        if len(oracion) < 3:
            continue
        for i in range(1, len(oracion) - 1):
            real = oracion[i + 1] if i + 1 < len(oracion) else None
            if not real:
                continue

            pred_bi  = predecir_bigrama(oracion[:i+1])
            pred_tri = predecir_trigrama(oracion[:i+1])

            aciertos_bi.append(int(pred_bi == real))
            aciertos_tri.append(int(pred_tri == real))

            # Perplejidad aproximada (Laplace)
            c_bi  = bi_conteos.get((oracion[i], real), 0)
            b_bi  = bi_base.get((oracion[i],), 0)
            p_bi  = (c_bi + 1) / (b_bi + V + 1)
            perp_bi.append(-np.log2(max(p_bi, 1e-10)))

            if i > 0:
                c_tri  = tri_conteos.get((oracion[i-1], oracion[i], real), 0)
                b_tri  = tri_base.get((oracion[i-1], oracion[i]), 0)
                p_tri  = (c_tri + 1) / (b_tri + V + 1)
                perp_tri.append(-np.log2(max(p_tri, 1e-10)))

    acc_bi  = np.mean(aciertos_bi)  * 100
    acc_tri = np.mean(aciertos_tri) * 100
    perp_bi_val  = 2 ** np.mean(perp_bi)
    perp_tri_val = 2 ** np.mean(perp_tri) if perp_tri else 0

    # Análisis de cobertura por longitud de oración
    longitudes = [3, 5, 7, 10, 15]
    acc_bi_lon, acc_tri_lon = [], []
    for lon in longitudes:
        test_lon = [o for o in oraciones_test if len(o) >= lon][:20]
        ab, at = [], []
        for o in test_lon:
            pred_b = predecir_bigrama(o[:lon-1])
            pred_t = predecir_trigrama(o[:lon-1])
            real   = o[lon-1] if lon-1 < len(o) else None
            if real:
                ab.append(int(pred_b == real))
                at.append(int(pred_t == real))
        acc_bi_lon.append(np.mean(ab) * 100 if ab else 0)
        acc_tri_lon.append(np.mean(at) * 100 if at else 0)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Experimento 4 — Modelo de N-gramas\nBigramas vs Trigramas para sugerencia de siguiente palabra',
                 fontsize=14, y=1.02)

    ax = axes[0]
    categorias = ['Bigrama', 'Trigrama']
    valores    = [acc_bi, acc_tri]
    bars = ax.bar(categorias, valores, color=[COLORES[0], COLORES[1]], width=0.4)
    ax.set_title('Precisión top-1')
    ax.set_ylabel('Precisión (%)')
    ax.set_ylim(0, max(valores) * 1.3)
    ax.grid(axis='y')
    for bar, val in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val:.2f}%', ha='center', va='bottom', fontsize=11,
                color='#F0EEFF', fontweight='bold')

    ax = axes[1]
    ax.bar(['Bigrama', 'Trigrama'], [perp_bi_val, perp_tri_val],
           color=[COLORES[0], COLORES[1]], width=0.4)
    ax.set_title('Perplejidad (menor = mejor)')
    ax.set_ylabel('Perplejidad')
    ax.grid(axis='y')
    for i, val in enumerate([perp_bi_val, perp_tri_val]):
        ax.text(i, val + 1, f'{val:.1f}', ha='center', va='bottom',
                fontsize=11, color='#F0EEFF')

    ax = axes[2]
    ax.plot(longitudes, acc_bi_lon,  'o-', color=COLORES[0],
            label='Bigrama',  markersize=8)
    ax.plot(longitudes, acc_tri_lon, 's-', color=COLORES[1],
            label='Trigrama', markersize=8)
    ax.set_title('Precisión por longitud de contexto')
    ax.set_xlabel('Longitud del contexto (palabras)')
    ax.set_ylabel('Precisión (%)')
    ax.legend()
    ax.grid()

    plt.tight_layout()
    ruta = os.path.join(SALIDA, 'experimento_ngramas.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#0F0F14')
    plt.close()
    print(f'  → Guardado: {ruta}')

    return {
        'precision_bigrama_pct':  round(acc_bi,  2),
        'precision_trigrama_pct': round(acc_tri, 2),
        'perp_bigrama':           round(perp_bi_val,  2),
        'perp_trigrama':          round(perp_tri_val, 2),
        'tiempo_bigrama_s':       round(t_bi,  3),
        'tiempo_trigrama_s':      round(t_tri, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# RESUMEN: tabla de resultados y gráfica de radar
# ═══════════════════════════════════════════════════════════════════════════

def generar_resumen(r_lev, r_fuz, r_som, r_ngr):
    print('\n[+] Generando resumen...')

    # Gráfica comparativa de tiempo de ejecución por módulo
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('SmartText — Resumen de Experimentos\nComparación general de métricas',
                 fontsize=14, y=1.02)

    # Tiempos por módulo
    ax = axes[0]
    modulos = ['Levenshtein\n(umbral=2)', 'Fuzzy\n(triangular)',
               'SOM\n(12×12)', 'Bigramas']
    tiempos = [
        r_lev['tiempos_ms'][1],
        r_fuz['tiempo_triangular_ms'],
        r_som['tiempos_s'][3] * 1000,  # convertir a ms
        r_ngr['tiempo_bigrama_s'] * 1000,
    ]
    bars = ax.bar(modulos, tiempos, color=COLORES[:4])
    ax.set_title('Tiempo de procesamiento por módulo')
    ax.set_ylabel('Tiempo (ms)')
    ax.set_yscale('log')
    ax.grid(axis='y')
    for bar, val in zip(bars, tiempos):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1,
                f'{val:.1f}ms', ha='center', va='bottom', fontsize=9,
                color='#F0EEFF')

    # Tabla de mejores configuraciones
    ax = axes[1]
    ax.axis('off')
    tabla_data = [
        ['Módulo', 'Config. óptima', 'Métrica principal'],
        ['Levenshtein', f'umbral=2', f'{r_lev["precision_pct"][1]:.1f}% precisión'],
        ['Lógica difusa', 'Triangular', f'Δ={r_fuz["diferencia_media"]:.4f} vs trapezoidal'],
        ['SOM', r_som['grid_optimo'], f'EQ={min(r_som["error_cuantizacion"]):.5f}'],
        ['N-gramas', 'Trigrama', f'{r_ngr["precision_trigrama_pct"]:.2f}% precisión'],
    ]
    tabla = ax.table(
        cellText=tabla_data[1:],
        colLabels=tabla_data[0],
        loc='center',
        cellLoc='center',
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1.2, 2.0)

    # Estilos de tabla
    for (r, c), cell in tabla.get_celld().items():
        cell.set_facecolor('#1A1A24' if r > 0 else '#7B61FF')
        cell.set_edgecolor('#2A2A3A')
        cell.set_text_props(color='#F0EEFF')

    ax.set_title('Configuraciones óptimas por módulo', pad=20)

    plt.tight_layout()
    ruta = os.path.join(SALIDA, 'resumen_experimentos.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor='#0F0F14')
    plt.close()
    print(f'  → Guardado: {ruta}')

    # Archivo de texto con todos los resultados
    ruta_txt = os.path.join(SALIDA, 'resumen_resultados.txt')
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        f.write('=' * 60 + '\n')
        f.write('SMARTTEXT — RESULTADOS DE EXPERIMENTACIÓN\n')
        f.write('=' * 60 + '\n\n')

        f.write('1. LEVENSHTEIN\n')
        f.write('-' * 40 + '\n')
        for i, u in enumerate(r_lev['umbrales']):
            f.write(f'  Umbral {u}: {r_lev["tiempos_ms"][i]}ms | '
                    f'{r_lev["candidatos"][i]} cands | '
                    f'{r_lev["precision_pct"][i]}% precisión\n')

        f.write('\n2. LÓGICA DIFUSA\n')
        f.write('-' * 40 + '\n')
        f.write(f'  Tiempo triangular: {r_fuz["tiempo_triangular_ms"]}ms\n')
        f.write(f'  Tiempo trapezoidal: {r_fuz["tiempo_trapezoidal_ms"]}ms\n')
        f.write(f'  Diferencia media: {r_fuz["diferencia_media"]}\n')

        f.write('\n3. SOM\n')
        f.write('-' * 40 + '\n')
        for i, g in enumerate(r_som['grids']):
            f.write(f'  Grid {g}: EQ={r_som["error_cuantizacion"][i]} | '
                    f'ET={r_som["error_topografico"][i]} | '
                    f'{r_som["tiempos_s"][i]}s\n')
        f.write(f'  Grid óptimo: {r_som["grid_optimo"]}\n')

        f.write('\n4. N-GRAMAS\n')
        f.write('-' * 40 + '\n')
        f.write(f'  Precisión bigrama:  {r_ngr["precision_bigrama_pct"]}%\n')
        f.write(f'  Precisión trigrama: {r_ngr["precision_trigrama_pct"]}%\n')
        f.write(f'  Perplejidad bigrama:  {r_ngr["perp_bigrama"]}\n')
        f.write(f'  Perplejidad trigrama: {r_ngr["perp_trigrama"]}\n')

    print(f'  → Guardado: {ruta_txt}')


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 50)
    print('SmartText — Suite de Experimentación')
    print('=' * 50)

    print('\nCargando vocabulario...')
    from corpus import cargar_vocabulario
    vocabulario, frecuencias = cargar_vocabulario()
    print(f'Vocabulario: {len(vocabulario)} palabras')

    r_lev = experimento_levenshtein(vocabulario)
    r_fuz = experimento_fuzzy()
    r_som = experimento_som(vocabulario, frecuencias)
    r_ngr = experimento_ngramas()

    generar_resumen(r_lev, r_fuz, r_som, r_ngr)

    print('\n' + '=' * 50)
    print('Experimentos completados.')
    print('Archivos generados en experiments/:')
    for f in ['experimento_levenshtein.png', 'experimento_fuzzy.png',
              'experimento_som.png', 'experimento_ngramas.png',
              'resumen_experimentos.png', 'resumen_resultados.txt']:
        print(f'  - {f}')
    print('=' * 50)