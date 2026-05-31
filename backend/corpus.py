"""
corpus.py — SmartText
Carga del corpus en español (nltk/cess_esp) y modelo de n-gramas para
sugerencia de siguiente palabra.

Referencia matemática:
    Jurafsky, D., & Martin, J. H. (2024). Speech and Language Processing (3rd ed.).
    Capítulo 3: N-gram Language Models.
    https://web.stanford.edu/~jurafsky/slp3/

    Probabilidad de bigrama con suavizado de Laplace:
        P(w_n | w_{n-1}) = (C(w_{n-1}, w_n) + 1) / (C(w_{n-1}) + |V|)
"""

import json
import os
from collections import Counter, defaultdict

import nltk
from nltk.corpus import cess_esp
from nltk.util import ngrams


# ── Descarga automática de recursos nltk ────────────────────────────────────
def _asegurar_recursos():
    recursos = ["cess_esp", "stopwords", "punkt", "punkt_tab"]
    for r in recursos:
        try:
            nltk.data.find(f"corpora/{r}")
        except LookupError:
            nltk.download(r, quiet=True)


# ── Carga y limpieza del corpus ──────────────────────────────────────────────
def cargar_vocabulario() -> tuple[set, dict]:
    """
    Carga el corpus cess_esp y devuelve:
        - vocabulario: conjunto de palabras válidas en español
        - frecuencias: dict {palabra: conteo} para el ranker difuso
    """
    _asegurar_recursos()

    palabras_raw = cess_esp.words()
    palabras = [w.lower() for w in palabras_raw if w.isalpha() and len(w) > 2]

    frecuencias = Counter(palabras)
    vocabulario = set(frecuencias.keys())

    return vocabulario, frecuencias


def frecuencia_normalizada(palabra: str, frecuencias: dict) -> float:
    """
    Normaliza la frecuencia de una palabra al rango [0, 1].
    Usa escala logarítmica para evitar que palabras muy comunes dominen.
    """
    import math
    freq = frecuencias.get(palabra.lower(), 0)
    max_freq = max(frecuencias.values()) if frecuencias else 1
    if freq == 0:
        return 0.0
    # log-normalización: más justa para comparar palabras raras vs comunes
    return math.log(freq + 1) / math.log(max_freq + 1)


# ── Modelo de N-gramas ───────────────────────────────────────────────────────
class ModeloBigramas:
    """
    Modelo de lenguaje basado en bigramas con suavizado de Laplace.

    La probabilidad de que w_n aparezca dado w_{n-1} es:
        P(w_n | w_{n-1}) = (C(w_{n-1}, w_n) + 1) / (C(w_{n-1}) + |V|)

    El suavizado de Laplace (add-1) evita probabilidad cero para bigramas
    no vistos en el corpus.
    """

    def __init__(self):
        self.bigramas: dict = defaultdict(Counter)   # {w1: {w2: conteo}}
        self.unigramas: Counter = Counter()           # {w: conteo}
        self.vocabulario_size: int = 0
        self.entrenado: bool = False

    def entrenar(self, oraciones: list[list[str]]):
        """
        Entrena el modelo sobre una lista de oraciones tokenizadas.

        Args:
            oraciones: lista de listas de tokens, ej. [["el", "perro", "corre"], ...]
        """
        for oracion in oraciones:
            tokens = [w.lower() for w in oracion if w.isalpha()]
            self.unigramas.update(tokens)
            for w1, w2 in ngrams(tokens, 2):
                self.bigramas[w1][w2] += 1

        self.vocabulario_size = len(self.unigramas)
        self.entrenado = True

    def entrenar_desde_corpus(self):
        """Entrena directamente desde cess_esp."""
        _asegurar_recursos()
        oraciones = cess_esp.sents()
        self.entrenar(oraciones)

    def probabilidad(self, w1: str, w2: str) -> float:
        """
        P(w2 | w1) con suavizado de Laplace.
        """
        w1, w2 = w1.lower(), w2.lower()
        conteo_bigrama = self.bigramas[w1][w2]
        conteo_unigrama = self.unigramas[w1]
        return (conteo_bigrama + 1) / (conteo_unigrama + self.vocabulario_size)

    def sugerir_siguiente(self, contexto: str, top_n: int = 5) -> list[tuple[str, float]]:
        """
        Dado el contexto (última palabra escrita), sugiere las top_n
        palabras más probables como continuación.

        Args:
            contexto: última palabra del texto escrito
            top_n:    número de sugerencias

        Returns:
            Lista de (palabra, probabilidad) ordenada descendente.
        """
        if not self.entrenado:
            self.entrenar_desde_corpus()

        ultima = contexto.strip().split()[-1].lower() if contexto.strip() else ""

        if not ultima or ultima not in self.bigramas:
            # Sin contexto o palabra desconocida: devolver las más frecuentes
            return [(w, c / sum(self.unigramas.values()))
                    for w, c in self.unigramas.most_common(top_n)]

        # Ordenar candidatos por probabilidad Laplace
        candidatos = []
        for w2, _ in self.bigramas[ultima].most_common(top_n * 3):
            prob = self.probabilidad(ultima, w2)
            candidatos.append((w2, prob))

        candidatos.sort(key=lambda x: x[1], reverse=True)
        return candidatos[:top_n]

    def guardar(self, ruta: str):
        """Serializa el modelo entrenado a JSON para persistencia."""
        data = {
            "unigramas": dict(self.unigramas),
            "bigramas": {k: dict(v) for k, v in self.bigramas.items()},
            "vocabulario_size": self.vocabulario_size,
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def cargar(self, ruta: str):
        """Carga un modelo previamente guardado."""
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"No se encontró el modelo en {ruta}")
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.unigramas = Counter(data["unigramas"])
        self.bigramas = defaultdict(Counter, {k: Counter(v) for k, v in data["bigramas"].items()})
        self.vocabulario_size = data["vocabulario_size"]
        self.entrenado = True


# ── Test rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Cargando vocabulario...")
    vocab, freqs = cargar_vocabulario()
    print(f"Vocabulario: {len(vocab)} palabras\n")

    print("Frecuencias de ejemplo:")
    for w in ["casa", "computadora", "xyz123"]:
        print(f"  '{w}': freq_norm={frecuencia_normalizada(w, freqs):.4f}")

    print("\nEntrenando modelo de bigramas (puede tardar ~10s)...")
    modelo = ModeloBigramas()
    modelo.entrenar_desde_corpus()
    print("Modelo entrenado.\n")

    print("Sugerencias después de 'el':")
    for palabra, prob in modelo.sugerir_siguiente("el"):
        print(f"  '{palabra}': P={prob:.6f}")

    print("\nSugerencias después de 'la':")
    for palabra, prob in modelo.sugerir_siguiente("la"):
        print(f"  '{palabra}': P={prob:.6f}")