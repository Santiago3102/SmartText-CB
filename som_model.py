"""
som_model.py — SmartText
Self-Organizing Map para clustering y visualización topológica del vocabulario.

Referencia matemática:
    Kohonen, T. (1982). Self-organized formation of topologically correct
    feature maps. Biological Cybernetics, 43(1), 59–69.

Regla de actualización (paso t):
    w_j(t+1) = w_j(t) + α(t) · h_{c,j}(t) · (x - w_j(t))

    donde:
        α(t)       = tasa de aprendizaje decreciente
        h_{c,j}(t) = exp(-||r_c - r_j||² / (2·σ(t)²))   [vecindad gaussiana]
        c          = nodo ganador (BMU): argmin_j ||x - w_j||
"""

import json
import os

import numpy as np
from minisom import MiniSom


# ── Representación vectorial de palabras ─────────────────────────────────────
def palabra_a_vector(palabra: str, dim: int = 20) -> np.ndarray:
    """
    Convierte una palabra a un vector numérico de dimensión `dim`.

    Estrategia: vector de características basadas en:
        - longitud normalizada
        - proporción de vocales
        - distribución de frecuencia de caracteres (bag of chars simplificado)

    No requiere embeddings externos — opera solo con propiedades del string.
    """
    vec = np.zeros(dim)
    if not palabra:
        return vec

    # Feature 0: longitud normalizada (max asumido 20 chars)
    vec[0] = min(len(palabra) / 20.0, 1.0)

    # Feature 1: proporción de vocales
    vocales = sum(1 for c in palabra if c in "aeiouáéíóúü")
    vec[1] = vocales / len(palabra)

    # Feature 2: proporción de consonantes
    vec[2] = 1.0 - vec[1]

    # Features 3–28: frecuencia relativa de cada letra a-z (26 letras)
    for i, letra in enumerate("abcdefghijklmnopqrstuvwxyz"):
        if 3 + i < dim:
            vec[3 + i] = palabra.count(letra) / len(palabra)

    return vec


def preparar_datos_som(vocabulario: set, frecuencias: dict,
                        min_freq: int = 5, max_palabras: int = 500) -> tuple:
    """
    Selecciona palabras representativas del vocabulario para entrenar el SOM.

    Args:
        vocabulario:  conjunto completo de palabras
        frecuencias:  dict {palabra: conteo}
        min_freq:     frecuencia mínima para incluir una palabra
        max_palabras: límite de palabras (SOM es O(n) en datos de entrenamiento)

    Returns:
        (palabras_seleccionadas, matriz_X) donde X tiene shape (n_palabras, dim_vector)
    """
    # Filtrar por frecuencia mínima y ordenar por frecuencia desc
    candidatas = [(w, frecuencias.get(w, 0)) for w in vocabulario
                  if frecuencias.get(w, 0) >= min_freq]
    candidatas.sort(key=lambda x: x[1], reverse=True)
    candidatas = candidatas[:max_palabras]

    palabras = [p for p, _ in candidatas]
    X = np.array([palabra_a_vector(p) for p in palabras])

    return palabras, X


# ── Entrenamiento del SOM ────────────────────────────────────────────────────
def entrenar_som(X: np.ndarray,
                 grid_x: int = 15,
                 grid_y: int = 15,
                 n_iter: int = 1000,
                 sigma: float = 1.5,
                 lr: float = 0.5,
                 seed: int = 42) -> MiniSom:
    """
    Entrena un SOM de grid_x × grid_y neuronas sobre los datos X.

    Args:
        X:      matriz de entrada (n_muestras, n_features)
        grid_x: dimensión x del mapa
        grid_y: dimensión y del mapa
        n_iter: número de iteraciones de entrenamiento
        sigma:  radio inicial de vecindad
        lr:     tasa de aprendizaje inicial
        seed:   semilla para reproducibilidad

    Returns:
        Objeto MiniSom entrenado
    """
    dim = X.shape[1]
    som = MiniSom(
        x=grid_x, y=grid_y,
        input_len=dim,
        sigma=sigma,
        learning_rate=lr,
        random_seed=seed
    )

    # Inicialización con PCA para convergencia más rápida
    som.pca_weights_init(X)

    # Entrenamiento
    som.train(X, n_iter, verbose=False)

    return som


def obtener_posicion_palabra(palabra: str, som: MiniSom) -> tuple[int, int]:
    """
    Retorna la posición (i, j) en el mapa SOM del BMU para `palabra`.
    Útil para buscar candidatos en la vecindad topológica.
    """
    vec = palabra_a_vector(palabra)
    return som.winner(vec)


def palabras_en_zona(palabra: str, som: MiniSom,
                     palabras: list, radio: int = 2) -> list[str]:
    """
    Devuelve palabras cuyo BMU está cerca del BMU de `palabra` en el mapa.
    Permite búsqueda topológica de candidatos similares.
    """
    pos_objetivo = obtener_posicion_palabra(palabra, som)
    cercanas = []

    for p in palabras:
        pos = obtener_posicion_palabra(p, som)
        distancia_mapa = abs(pos[0] - pos_objetivo[0]) + abs(pos[1] - pos_objetivo[1])
        if distancia_mapa <= radio and p != palabra:
            cercanas.append(p)

    return cercanas


def graficar_som(som: MiniSom, palabras: list, X: np.ndarray,
                 guardar_en: str = None):
    """
    Genera el mapa de distancias U-Matrix con etiquetas de palabras.
    Visualización central del SOM para la presentación.
    """
    import matplotlib
    if guardar_en:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 10))

    # U-Matrix (distancias entre neuronas vecinas = topología aprendida)
    u_matrix = som.distance_map()
    im = ax.pcolormesh(u_matrix.T, cmap="bone_r", alpha=0.85)
    plt.colorbar(im, ax=ax, label="Distancia inter-neuronal")

    # Posicionar etiquetas de palabras (solo las más frecuentes para no saturar)
    posiciones_usadas = {}
    for i, (p, x) in enumerate(zip(palabras[:80], X[:80])):
        pos = som.winner(x)
        key = pos
        if key not in posiciones_usadas:
            posiciones_usadas[key] = []
        posiciones_usadas[key].append(p)

    for pos, ps in posiciones_usadas.items():
        etiqueta = ps[0]  # solo la primera palabra por nodo
        ax.text(pos[0] + 0.5, pos[1] + 0.5, etiqueta,
                ha="center", va="center", fontsize=7,
                color="darkblue", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.6))

    ax.set_title("SOM — Mapa de Vocabulario SmartText\n(U-Matrix: zonas oscuras = fronteras entre clusters)",
                 fontsize=12)
    ax.set_xlabel("Neurona X"); ax.set_ylabel("Neurona Y")
    plt.tight_layout()

    if guardar_en:
        plt.savefig(guardar_en, dpi=150, bbox_inches="tight")
        print(f"Mapa SOM guardado en: {guardar_en}")
    else:
        plt.show()
    plt.close()


def guardar_som(som: MiniSom, palabras: list, ruta_base: str):
    """Persiste el SOM entrenado."""
    np.save(f"{ruta_base}_pesos.npy", som.get_weights())
    with open(f"{ruta_base}_palabras.json", "w", encoding="utf-8") as f:
        json.dump(palabras, f, ensure_ascii=False)


def cargar_som(ruta_base: str, grid_x: int = 15, grid_y: int = 15,
               dim: int = 20) -> tuple[MiniSom, list]:
    """Carga un SOM previamente entrenado."""
    pesos = np.load(f"{ruta_base}_pesos.npy")
    som = MiniSom(grid_x, grid_y, dim, sigma=1.5, learning_rate=0.5)
    som._weights = pesos

    with open(f"{ruta_base}_palabras.json", "r", encoding="utf-8") as f:
        palabras = json.load(f)

    return som, palabras


# ── Test rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Cargando vocabulario...")
    import sys; sys.path.insert(0, "/home/claude/smarttext")
    from corpus import cargar_vocabulario

    vocab, freqs = cargar_vocabulario()
    palabras, X = preparar_datos_som(vocab, freqs, min_freq=5, max_palabras=300)
    print(f"Entrenando SOM con {len(palabras)} palabras...")

    som = entrenar_som(X, grid_x=12, grid_y=12, n_iter=500)
    print("SOM entrenado.\n")

    # Buscar vecinos topológicos
    test_palabras = ["casa", "gobierno", "trabajo"]
    for p in test_palabras:
        if p in palabras:
            vecinos = palabras_en_zona(p, som, palabras, radio=2)
            print(f"Vecinos de '{p}': {vecinos[:5]}")

    print("\nGenerando mapa SOM...")
    graficar_som(som, palabras, X, guardar_en="/home/claude/smarttext/mapa_som.png")