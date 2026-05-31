"""
engine.py — SmartText
Pipeline central de inteligencia. Integra los 5 módulos backend.

Flujo por llamada a procesar_texto():
    1. Tokenizar entrada con nltk
    2. Por cada token:
        a. Verificar si está en el vocabulario
        b. Si no: buscar candidatos con Levenshtein
        c. Rankear candidatos con lógica difusa
        d. Aplicar historial del usuario (boost/penalización)
    3. Sugerir siguiente palabra con modelo de bigramas
    4. Actualizar vocabulario del usuario
"""

import os
import sys

# Asegurar que los módulos del proyecto son encontrables
sys.path.insert(0, os.path.dirname(__file__))

import nltk
from nltk.tokenize import word_tokenize

from levenshtein import buscar_candidatos
from corpus import cargar_vocabulario, frecuencia_normalizada, ModeloBigramas
from fuzzy_ranker import rankear_candidatos
from som_model import (preparar_datos_som, entrenar_som,
                       obtener_posicion_palabra, guardar_som, cargar_som)
from persistencia import (cargar_datos, guardar_datos,
                           registrar_correccion_aceptada,
                           registrar_correccion_rechazada,
                           registrar_palabra_usada,
                           obtener_correccion_preferida,
                           es_rechazada, frecuencias_usuario, estadisticas)


RUTA_MODELO_BIGRAMAS = os.path.join(os.path.dirname(__file__), "modelo_bigramas.json")
RUTA_SOM             = os.path.join(os.path.dirname(__file__), "som_model")
RUTA_USUARIO         = os.path.join(os.path.dirname(__file__), "usuario_data.json")


class SmartTextEngine:
    """
    Motor principal de SmartText.

    Uso típico:
        engine = SmartTextEngine()
        engine.inicializar()                          # carga modelos (una vez)
        resultado = engine.procesar_texto("haver")    # análisis en tiempo real
        engine.aceptar_correccion("haver", "haber")   # feedback del usuario
    """

    def __init__(self):
        self.vocabulario: set = set()
        self.frecuencias: dict = {}
        self.modelo_bigramas: ModeloBigramas = None
        self.som = None
        self.palabras_som: list = []
        self.datos_usuario: dict = {}
        self.listo: bool = False

    # ── Inicialización ───────────────────────────────────────────────────────

    def inicializar(self, callback_progreso=None):
        """
        Carga o entrena todos los modelos. Llama callback_progreso(msg)
        en cada paso para actualizar una barra de carga en la UI.
        """
        def _log(msg):
            if callback_progreso:
                callback_progreso(msg)
            else:
                print(msg)

        _log("Cargando vocabulario...")
        self.vocabulario, self.frecuencias = cargar_vocabulario()

        _log("Cargando datos del usuario...")
        self.datos_usuario = cargar_datos(RUTA_USUARIO)

        # Enriquecer vocabulario con palabras del usuario
        freq_usuario = frecuencias_usuario(self.datos_usuario)
        for palabra, conteo in freq_usuario.items():
            self.vocabulario.add(palabra)
            self.frecuencias[palabra] = self.frecuencias.get(palabra, 0) + conteo * 3  # boost usuario

        _log("Cargando modelo de bigramas...")
        self.modelo_bigramas = ModeloBigramas()
        if os.path.exists(RUTA_MODELO_BIGRAMAS):
            self.modelo_bigramas.cargar(RUTA_MODELO_BIGRAMAS)
            _log("  → Modelo cargado desde caché.")
        else:
            _log("  → Entrenando modelo (primera vez, ~15s)...")
            self.modelo_bigramas.entrenar_desde_corpus()
            self.modelo_bigramas.guardar(RUTA_MODELO_BIGRAMAS)
            _log("  → Modelo guardado.")

        _log("Cargando SOM...")
        ruta_pesos = RUTA_SOM + "_pesos.npy"
        if os.path.exists(ruta_pesos):
            self.som, self.palabras_som = cargar_som(RUTA_SOM)
            _log("  → SOM cargado desde caché.")
        else:
            _log("  → Entrenando SOM (primera vez, ~20s)...")
            _, X = preparar_datos_som(self.vocabulario, self.frecuencias,
                                       min_freq=5, max_palabras=400)
            palabras_tmp, X = preparar_datos_som(self.vocabulario, self.frecuencias,
                                                  min_freq=5, max_palabras=400)
            self.palabras_som = palabras_tmp
            self.som = entrenar_som(X, grid_x=15, grid_y=15, n_iter=800)
            guardar_som(self.som, self.palabras_som, RUTA_SOM)
            _log("  → SOM guardado.")

        self.listo = True
        _log("SmartText listo.")

    # ── Procesamiento principal ──────────────────────────────────────────────

    def procesar_texto(self, texto: str,
                       max_distancia: int = 2,
                       top_sugerencias: int = 5) -> dict:
        """
        Analiza el texto completo y devuelve correcciones y sugerencias.

        Args:
            texto:            texto escrito por el usuario
            max_distancia:    umbral Levenshtein para considerar una palabra error
            top_sugerencias:  número de correcciones a mostrar

        Returns:
            {
                "tokens": [...],
                "errores": {
                    "palabra": [
                        {"sugerencia": str, "distancia": int, "relevancia": float},
                        ...
                    ]
                },
                "siguiente_palabra": [(palabra, prob), ...]
            }
        """
        if not self.listo:
            raise RuntimeError("Llama a inicializar() primero.")

        # Tokenizar
        try:
            tokens = word_tokenize(texto.lower(), language="spanish")
        except Exception:
            tokens = texto.lower().split()

        tokens_alfa = [t for t in tokens if t.isalpha()]

        errores = {}

        for token in tokens_alfa:
            # Registrar uso en vocabulario personal
            self.datos_usuario = registrar_palabra_usada(self.datos_usuario, token)

            # Si está en el vocabulario: correcto
            if token in self.vocabulario:
                continue

            # Verificar historial: ¿el usuario ya corrigió esto antes?
            preferida = obtener_correccion_preferida(self.datos_usuario, token)

            # Buscar candidatos con Levenshtein
            candidatos = buscar_candidatos(token, self.vocabulario,
                                            max_distancia=max_distancia,
                                            top_n=top_sugerencias * 3)

            if not candidatos:
                continue

            # Rankear con lógica difusa
            rankeados = rankear_candidatos(candidatos, self.frecuencias)

            # Filtrar rechazadas por el usuario
            rankeados = [(p, d, r) for p, d, r in rankeados
                         if not es_rechazada(self.datos_usuario, token, p)]

            # Si hay preferida histórica, ponerla primera
            if preferida:
                rankeados = [(preferida, 0, 1.0)] + [
                    x for x in rankeados if x[0] != preferida
                ]

            errores[token] = [
                {"sugerencia": p, "distancia": d, "relevancia": round(r, 4)}
                for p, d, r in rankeados[:top_sugerencias]
            ]

        # Sugerencia de siguiente palabra
        siguiente = self.modelo_bigramas.sugerir_siguiente(texto, top_n=5)

        # Persistir cambios del usuario de forma diferida (cada 10 tokens)
        if len(tokens_alfa) % 10 == 0:
            guardar_datos(self.datos_usuario, RUTA_USUARIO)

        return {
            "tokens": tokens_alfa,
            "errores": errores,
            "siguiente_palabra": [{"palabra": p, "prob": round(pr, 6)}
                                   for p, pr in siguiente],
        }

    # ── Feedback del usuario ─────────────────────────────────────────────────

    def aceptar_correccion(self, error: str, correccion: str):
        """El usuario aceptó una sugerencia. Guardar y reforzar."""
        self.datos_usuario = registrar_correccion_aceptada(
            self.datos_usuario, error, correccion)
        # Añadir al vocabulario con boost
        self.vocabulario.add(correccion)
        guardar_datos(self.datos_usuario, RUTA_USUARIO)

    def rechazar_correccion(self, error: str, correccion: str):
        """El usuario rechazó una sugerencia."""
        self.datos_usuario = registrar_correccion_rechazada(
            self.datos_usuario, error, correccion)
        guardar_datos(self.datos_usuario, RUTA_USUARIO)

    def estadisticas_usuario(self) -> dict:
        return estadisticas(self.datos_usuario)


# ── Test de integración ──────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = SmartTextEngine()
    engine.inicializar()

    textos_prueba = [
        "el gobierno tomo una desicion",
        "la computdora funciona bien",
        "quiero aber si puedo",
    ]

    for texto in textos_prueba:
        print(f"\n{'='*50}")
        print(f"Texto: '{texto}'")
        resultado = engine.procesar_texto(texto)

        if resultado["errores"]:
            print("Errores detectados:")
            for palabra, sugerencias in resultado["errores"].items():
                print(f"  '{palabra}':")
                for s in sugerencias:
                    print(f"    → '{s['sugerencia']}' | dist={s['distancia']} | relevancia={s['relevancia']}")
        else:
            print("Sin errores ortográficos.")

        print("Siguiente palabra sugerida:")
        for s in resultado["siguiente_palabra"][:3]:
            print(f"  '{s['palabra']}' (P={s['prob']:.6f})")