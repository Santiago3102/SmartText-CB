"""
persistencia.py — SmartText
Almacenamiento local del historial de uso para aprendizaje adaptativo.

El sistema aprende del usuario registrando:
    - correcciones aceptadas (refuerza la asociación error→corrección)
    - correcciones rechazadas (penaliza sugerencias no útiles)
    - vocabulario propio (palabras que el usuario usa frecuentemente)

Los datos se guardan en JSON local — sin dependencias externas.
"""

import json
import os
from collections import Counter
from datetime import datetime


RUTA_DEFAULT = os.path.join(os.path.dirname(__file__), "usuario_data.json")


def _estructura_vacia() -> dict:
    return {
        "version": "1.0",
        "creado": datetime.now().isoformat(),
        "ultima_actualizacion": datetime.now().isoformat(),
        "correcciones_aceptadas": {},    # {error: {correccion: conteo}}
        "correcciones_rechazadas": {},   # {error: [correcciones_rechazadas]}
        "vocabulario_usuario": {},       # {palabra: conteo_de_uso}
        "sesiones": 0,
        "total_correcciones": 0,
    }


def cargar_datos(ruta: str = RUTA_DEFAULT) -> dict:
    """Carga el perfil del usuario. Si no existe, crea uno nuevo."""
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        datos["sesiones"] = datos.get("sesiones", 0) + 1
        return datos
    return _estructura_vacia()


def guardar_datos(datos: dict, ruta: str = RUTA_DEFAULT):
    """Persiste el perfil del usuario al disco."""
    datos["ultima_actualizacion"] = datetime.now().isoformat()
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def registrar_correccion_aceptada(datos: dict, error: str, correccion: str) -> dict:
    """
    El usuario aceptó una sugerencia de corrección.
    Refuerza la asociación error→corrección para futuros usos.
    """
    error = error.lower().strip()
    correccion = correccion.lower().strip()

    if error not in datos["correcciones_aceptadas"]:
        datos["correcciones_aceptadas"][error] = {}

    conteo_actual = datos["correcciones_aceptadas"][error].get(correccion, 0)
    datos["correcciones_aceptadas"][error][correccion] = conteo_actual + 1
    datos["total_correcciones"] += 1

    # También suma al vocabulario del usuario
    datos = registrar_palabra_usada(datos, correccion)

    return datos


def registrar_correccion_rechazada(datos: dict, error: str, correccion: str) -> dict:
    """
    El usuario rechazó una sugerencia.
    Se registra para reducir la prioridad de esa sugerencia.
    """
    error = error.lower().strip()
    correccion = correccion.lower().strip()

    if error not in datos["correcciones_rechazadas"]:
        datos["correcciones_rechazadas"][error] = []

    if correccion not in datos["correcciones_rechazadas"][error]:
        datos["correcciones_rechazadas"][error].append(correccion)

    return datos


def registrar_palabra_usada(datos: dict, palabra: str) -> dict:
    """Incrementa el contador de uso de una palabra en el vocabulario personal."""
    palabra = palabra.lower().strip()
    if len(palabra) < 2:
        return datos
    conteo = datos["vocabulario_usuario"].get(palabra, 0)
    datos["vocabulario_usuario"][palabra] = conteo + 1
    return datos


def obtener_correccion_preferida(datos: dict, error: str) -> str | None:
    """
    Si el usuario ya corrigió este error antes, devuelve la corrección
    más frecuentemente aceptada. None si no hay historial.
    """
    error = error.lower().strip()
    historial = datos["correcciones_aceptadas"].get(error, {})
    if not historial:
        return None
    return max(historial, key=historial.get)


def es_rechazada(datos: dict, error: str, correccion: str) -> bool:
    """Indica si el usuario ya rechazó esta corrección para este error."""
    error = error.lower().strip()
    correccion = correccion.lower().strip()
    return correccion in datos["correcciones_rechazadas"].get(error, [])


def frecuencias_usuario(datos: dict) -> Counter:
    """Retorna las frecuencias del vocabulario personal como Counter."""
    return Counter(datos["vocabulario_usuario"])


def estadisticas(datos: dict) -> dict:
    """Resumen del perfil del usuario para mostrar en la UI."""
    return {
        "sesiones": datos.get("sesiones", 0),
        "total_correcciones": datos.get("total_correcciones", 0),
        "palabras_aprendidas": len(datos.get("vocabulario_usuario", {})),
        "errores_frecuentes": sorted(
            datos.get("correcciones_aceptadas", {}).keys(),
            key=lambda e: sum(datos["correcciones_aceptadas"][e].values()),
            reverse=True
        )[:5],
        "ultima_sesion": datos.get("ultima_actualizacion", "—"),
    }


# ── Test rápido ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    ruta_test = os.path.join(tempfile.gettempdir(), "smarttext_test.json")
    print(f"Usando archivo temporal: {ruta_test}\n")

    # Simular sesión de uso
    datos = cargar_datos(ruta_test)

    datos = registrar_correccion_aceptada(datos, "haver", "haber")
    datos = registrar_correccion_aceptada(datos, "haver", "haber")
    datos = registrar_correccion_rechazada(datos, "haver", "haber")  # edge case
    datos = registrar_palabra_usada(datos, "computadora")
    datos = registrar_palabra_usada(datos, "computadora")
    datos = registrar_palabra_usada(datos, "universidad")

    guardar_datos(datos, ruta_test)
    datos_recargados = cargar_datos(ruta_test)

    print("Corrección preferida para 'haver':",
          obtener_correccion_preferida(datos_recargados, "haver"))

    print("\nEstadísticas del usuario:")
    stats = estadisticas(datos_recargados)
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Limpiar
    os.remove(ruta_test)
    print("\nTest completado.")