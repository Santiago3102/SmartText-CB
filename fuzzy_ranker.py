"""
fuzzy_ranker.py — SmartText
Sistema de inferencia difusa (Mamdani) para rankear candidatos de corrección.

Entradas:
    - distancia normalizada de Levenshtein ∈ [0, 1]
    - frecuencia normalizada de la palabra en el corpus ∈ [0, 1]

Salida:
    - relevancia de la sugerencia ∈ [0, 1]

Referencia matemática:
    Zadeh, L. A. (1965). Fuzzy sets. Information and Control, 8(3), 338–353.
    Mamdani, E. H., & Assilian, S. (1975). An experiment in linguistic synthesis
    with a fuzzy logic controller. International Journal of Man-Machine Studies,
    7(1), 1–13.

Defuzzificación por centroide:
    z* = ∫ z · μ_salida(z) dz / ∫ μ_salida(z) dz
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


def construir_sistema_difuso():
    """
    Construye y retorna el sistema de inferencia difusa Mamdani.

    Variables lingüísticas:
        distancia:   [cercana, media, lejana]
        frecuencia:  [baja, media, alta]
        relevancia:  [muy_baja, baja, media, alta, muy_alta]

    Reglas (base de conocimiento):
        R1: SI distancia=cercana  Y frecuencia=alta  → relevancia=muy_alta
        R2: SI distancia=cercana  Y frecuencia=media → relevancia=alta
        R3: SI distancia=cercana  Y frecuencia=baja  → relevancia=media
        R4: SI distancia=media    Y frecuencia=alta  → relevancia=alta
        R5: SI distancia=media    Y frecuencia=media → relevancia=media
        R6: SI distancia=media    Y frecuencia=baja  → relevancia=baja
        R7: SI distancia=lejana                      → relevancia=muy_baja
    """

    # ── Universos de discurso ────────────────────────────────────────────────
    universo_dist = np.linspace(0, 1, 100)
    universo_freq = np.linspace(0, 1, 100)
    universo_relev = np.linspace(0, 1, 100)

    # ── Variables antecedentes y consecuente ────────────────────────────────
    distancia  = ctrl.Antecedent(universo_dist,  "distancia")
    frecuencia = ctrl.Antecedent(universo_freq,  "frecuencia")
    relevancia = ctrl.Consequent(universo_relev, "relevancia")

    # ── Funciones de membresía — Distancia ──────────────────────────────────
    # Triangulares: intuitivas, computacionalmente eficientes
    distancia["cercana"] = fuzz.trimf(universo_dist, [0.0, 0.0, 0.35])
    distancia["media"]   = fuzz.trimf(universo_dist, [0.2, 0.5, 0.8])
    distancia["lejana"]  = fuzz.trimf(universo_dist, [0.65, 1.0, 1.0])

    # ── Funciones de membresía — Frecuencia ─────────────────────────────────
    frecuencia["baja"]  = fuzz.trimf(universo_freq, [0.0, 0.0, 0.4])
    frecuencia["media"] = fuzz.trimf(universo_freq, [0.25, 0.5, 0.75])
    frecuencia["alta"]  = fuzz.trimf(universo_freq, [0.6, 1.0, 1.0])

    # ── Funciones de membresía — Relevancia (salida) ─────────────────────────
    relevancia["muy_baja"] = fuzz.trimf(universo_relev, [0.0,  0.0,  0.25])
    relevancia["baja"]     = fuzz.trimf(universo_relev, [0.1,  0.25, 0.45])
    relevancia["media"]    = fuzz.trimf(universo_relev, [0.3,  0.5,  0.7])
    relevancia["alta"]     = fuzz.trimf(universo_relev, [0.55, 0.75, 0.9])
    relevancia["muy_alta"] = fuzz.trimf(universo_relev, [0.75, 1.0,  1.0])

    # ── Base de reglas ───────────────────────────────────────────────────────
    reglas = [
        ctrl.Rule(distancia["cercana"] & frecuencia["alta"],  relevancia["muy_alta"]),
        ctrl.Rule(distancia["cercana"] & frecuencia["media"], relevancia["alta"]),
        ctrl.Rule(distancia["cercana"] & frecuencia["baja"],  relevancia["media"]),
        ctrl.Rule(distancia["media"]   & frecuencia["alta"],  relevancia["alta"]),
        ctrl.Rule(distancia["media"]   & frecuencia["media"], relevancia["media"]),
        ctrl.Rule(distancia["media"]   & frecuencia["baja"],  relevancia["baja"]),
        ctrl.Rule(distancia["lejana"],                        relevancia["muy_baja"]),
    ]

    sistema = ctrl.ControlSystem(reglas)
    return ctrl.ControlSystemSimulation(sistema), distancia, frecuencia, relevancia


# Instancia global (se crea una sola vez)
_simulacion = None
_var_distancia = None
_var_frecuencia = None
_var_relevancia = None


def _get_simulacion():
    global _simulacion, _var_distancia, _var_frecuencia, _var_relevancia
    if _simulacion is None:
        _simulacion, _var_distancia, _var_frecuencia, _var_relevancia = construir_sistema_difuso()
    return _simulacion, _var_distancia, _var_frecuencia, _var_relevancia


def calcular_relevancia(dist_norm: float, freq_norm: float) -> float:
    """
    Calcula la relevancia difusa de una sugerencia.

    Args:
        dist_norm:  distancia de Levenshtein normalizada ∈ [0, 1]
        freq_norm:  frecuencia normalizada del corpus ∈ [0, 1]

    Returns:
        Valor de relevancia defuzzificado ∈ [0, 1]
    """
    sim, _, _, _ = _get_simulacion()

    # Clampear entradas al universo
    dist_norm = float(np.clip(dist_norm, 0.0, 1.0))
    freq_norm = float(np.clip(freq_norm, 0.0, 1.0))

    sim.input["distancia"]  = dist_norm
    sim.input["frecuencia"] = freq_norm

    try:
        sim.compute()
        return float(sim.output["relevancia"])
    except Exception:
        # Fallback determinístico si el sistema falla (ej. inputs extremos)
        return max(0.0, (1.0 - dist_norm) * 0.6 + freq_norm * 0.4)


def rankear_candidatos(candidatos: list, frecuencias: dict) -> list:
    """
    Aplica el sistema difuso a una lista de candidatos y los reordena.

    Args:
        candidatos:  lista de (palabra, distancia_int, distancia_norm)
                     tal como la devuelve levenshtein.buscar_candidatos()
        frecuencias: dict {palabra: conteo} del corpus

    Returns:
        Lista de (palabra, distancia, relevancia_difusa) ordenada por
        relevancia descendente.
    """
    from corpus import frecuencia_normalizada

    resultado = []
    for palabra, dist_int, dist_norm in candidatos:
        freq_norm = frecuencia_normalizada(palabra, frecuencias)
        relevancia = calcular_relevancia(dist_norm, freq_norm)
        resultado.append((palabra, dist_int, relevancia))

    resultado.sort(key=lambda x: x[2], reverse=True)
    return resultado


def graficar_membresias(guardar_en: str = None):
    """
    Genera gráfica de las funciones de membresía para el informe/presentación.

    Args:
        guardar_en: ruta de archivo (ej. 'membresias.png'). Si es None, muestra en pantalla.
    """
    import matplotlib
    if guardar_en:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _, dist_var, freq_var, relev_var = _get_simulacion()

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.suptitle("Funciones de Membresía — Sistema Difuso SmartText", fontsize=13)

    # Distancia
    ax = axes[0]
    for termino, color in zip(["cercana", "media", "lejana"], ["#2ecc71", "#f39c12", "#e74c3c"]):
        ax.plot(dist_var.universe, dist_var[termino].mf, label=termino, color=color, lw=2)
    ax.set_title("Distancia de Levenshtein (normalizada)")
    ax.set_xlabel("d ∈ [0, 1]"); ax.set_ylabel("μ(d)")
    ax.legend(); ax.grid(alpha=0.3)

    # Frecuencia
    ax = axes[1]
    for termino, color in zip(["baja", "media", "alta"], ["#e74c3c", "#f39c12", "#2ecc71"]):
        ax.plot(freq_var.universe, freq_var[termino].mf, label=termino, color=color, lw=2)
    ax.set_title("Frecuencia en corpus (normalizada)")
    ax.set_xlabel("f ∈ [0, 1]"); ax.set_ylabel("μ(f)")
    ax.legend(); ax.grid(alpha=0.3)

    # Relevancia
    ax = axes[2]
    colores = ["#c0392b", "#e74c3c", "#f39c12", "#27ae60", "#2ecc71"]
    for termino, color in zip(["muy_baja", "baja", "media", "alta", "muy_alta"], colores):
        ax.plot(relev_var.universe, relev_var[termino].mf, label=termino, color=color, lw=2)
    ax.set_title("Relevancia de sugerencia (salida)")
    ax.set_xlabel("r ∈ [0, 1]"); ax.set_ylabel("μ(r)")
    ax.legend(); ax.grid(alpha=0.3)

    plt.tight_layout()

    if guardar_en:
        plt.savefig(guardar_en, dpi=150, bbox_inches="tight")
        print(f"Gráfica guardada en: {guardar_en}")
    else:
        plt.show()
    plt.close()


# ── Test rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test Sistema Difuso ===\n")

    casos = [
        (0.1, 0.9, "Muy cercana + muy frecuente → esperado: muy alta"),
        (0.1, 0.2, "Muy cercana + poco frecuente → esperado: media"),
        (0.5, 0.8, "Distancia media + frecuente  → esperado: alta"),
        (0.5, 0.3, "Distancia media + poco freq  → esperado: media-baja"),
        (0.9, 0.9, "Muy lejana + muy frecuente   → esperado: muy baja"),
    ]

    for dist, freq, descripcion in casos:
        rel = calcular_relevancia(dist, freq)
        print(f"  dist={dist:.1f}, freq={freq:.1f} → relevancia={rel:.4f}  | {descripcion}")

    print("\nGenerando gráfica de membresías...")
    graficar_membresias(guardar_en="/home/claude/smarttext/membresias.png")