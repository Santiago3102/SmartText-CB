"""
levenshtein.py — SmartText
Módulo de corrección ortográfica basado en distancia de Levenshtein.

Referencia matemática:
    Levenshtein, V. I. (1966). Binary codes capable of correcting deletions,
    insertions, and reversals. Soviet Physics Doklady, 10(8), 707–710.
"""


def distancia_levenshtein(a: str, b: str) -> int:
    """
    Calcula la distancia de edición mínima entre dos strings.

    Recurrencia:
        d[i][j] = 0                          si i=0 y j=0
        d[i][j] = i                          si j=0
        d[i][j] = j                          si i=0
        d[i][j] = d[i-1][j-1]               si a[i] == b[j]
        d[i][j] = 1 + min(d[i-1][j],        (eliminación)
                          d[i][j-1],         (inserción)
                          d[i-1][j-1])       (sustitución)

    Complejidad: O(m * n) tiempo, O(m * n) espacio.
    """
    m, n = len(a), len(b)

    # Matriz de programación dinámica
    d = [[0] * (n + 1) for _ in range(m + 1)]

    # Casos base: transformar string vacío
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j

    # Llenado de la matriz
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                d[i][j] = d[i - 1][j - 1]          # Sin costo: mismo caracter
            else:
                d[i][j] = 1 + min(
                    d[i - 1][j],                     # Eliminación
                    d[i][j - 1],                     # Inserción
                    d[i - 1][j - 1]                  # Sustitución
                )

    return d[m][n]


def distancia_normalizada(a: str, b: str) -> float:
    """
    Normaliza la distancia al rango [0, 1] dividiendo por la longitud máxima.
    Útil para comparar palabras de distinto largo.
    """
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 0.0
    return distancia_levenshtein(a, b) / max_len


def buscar_candidatos(palabra: str, vocabulario: set, max_distancia: int = 2, top_n: int = 10) -> list:
    """
    Encuentra las palabras del vocabulario más cercanas a `palabra`.

    Args:
        palabra:        Palabra posiblemente mal escrita.
        vocabulario:    Conjunto de palabras válidas.
        max_distancia:  Umbral máximo de distancia de Levenshtein.
        top_n:          Número máximo de candidatos a devolver.

    Returns:
        Lista de tuplas (palabra_candidata, distancia, distancia_normalizada)
        ordenada por distancia ascendente.
    """
    palabra = palabra.lower().strip()

    # Optimización: filtrar por diferencia de longitud antes de calcular
    candidatos = []
    for w in vocabulario:
        diff_len = abs(len(w) - len(palabra))
        if diff_len > max_distancia:
            continue  # Imposible que la distancia sea <= max_distancia

        dist = distancia_levenshtein(palabra, w)
        if dist <= max_distancia:
            dist_norm = dist / max(len(palabra), len(w))
            candidatos.append((w, dist, dist_norm))

    # Ordenar por distancia exacta, luego alfabéticamente para desempate
    candidatos.sort(key=lambda x: (x[1], x[0]))

    return candidatos[:top_n]


# ── Test rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Test Levenshtein ===\n")

    pares = [
        ("haber", "haver"),
        ("casa", "caza"),
        ("python", "pithon"),
        ("computadora", "computdora"),
    ]

    for a, b in pares:
        d = distancia_levenshtein(a, b)
        dn = distancia_normalizada(a, b)
        print(f"  '{a}' ↔ '{b}': distancia={d}, normalizada={dn:.3f}")

    print("\n=== Búsqueda en vocabulario de prueba ===\n")
    vocab_prueba = {"haber", "saber", "caber", "beber", "tener", "poder",
                    "hacer", "haver", "abrir", "vivir", "salir", "venir"}

    candidatos = buscar_candidatos("haver", vocab_prueba)
    for palabra, dist, dist_norm in candidatos:
        print(f"  '{palabra}': distancia={dist}, normalizada={dist_norm:.3f}")