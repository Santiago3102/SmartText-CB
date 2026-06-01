# SmartText — Corrector Ortográfico Inteligente

SmartText es una aplicación desarrollada en **Python** con interfaz gráfica en **Kivy**, diseñada para analizar texto en español, detectar posibles errores ortográficos y sugerir correcciones inteligentes en tiempo real.

El proyecto combina varias técnicas vistas en Computación Blanda e Inteligencia Artificial, como:

* Distancia de Levenshtein.
* Lógica difusa.
* Modelos de lenguaje con n-gramas.
* Self-Organizing Maps, SOM.
* Aprendizaje adaptativo basado en el historial del usuario.

La aplicación funciona como un corrector inteligente que no solo propone correcciones, sino que también aprende de las decisiones del usuario, recordando correcciones aceptadas, rechazadas y palabras usadas frecuentemente.

---

## Características principales

* Corrección ortográfica en español.
* Detección de palabras posiblemente mal escritas.
* Sugerencias ordenadas por relevancia.
* Ranking de candidatos mediante lógica difusa.
* Sugerencia de siguiente palabra usando modelo de bigramas.
* Aprendizaje adaptativo según el historial del usuario.
* Interfaz gráfica moderna con Kivy.
* Subrayado visual de errores en tiempo real.
* Chips táctiles para aceptar sugerencias.
* Botón para deshacer la última corrección.
* Pantalla de estadísticas del usuario.
* Visualización de mapa SOM para agrupamiento de vocabulario.
* Módulo de experimentación con generación de gráficas comparativas.

---

## Estructura del proyecto

```txt
SmarTextCB/
├── requirements.txt
├── .gitignore
├── backend/
│   ├── corpus.py
│   ├── engine.py
│   ├── fuzzy_ranker.py
│   ├── levenshtein.py
│   ├── persistencia.py
│   └── som_model.py
├── experiments/
│   └── experimentos.py
└── ui/
    ├── main.py
    ├── screens.py
    └── smarttext.kv
```

---

## Tecnologías utilizadas

El proyecto usa las siguientes librerías principales:

```txt
kivy>=2.3.0
nltk>=3.8
minisom>=2.3
scikit-fuzzy>=0.4.2
numpy>=1.24
matplotlib>=3.7
plotly>=5.0
scipy>=1.10
networkx>=3.0
```

### Descripción de tecnologías

| Tecnología   | Uso en el proyecto                                                      |
| ------------ | ----------------------------------------------------------------------- |
| Kivy         | Interfaz gráfica de la aplicación                                       |
| NLTK         | Corpus en español, tokenización y procesamiento de lenguaje             |
| MiniSom      | Entrenamiento del mapa autoorganizado SOM                               |
| scikit-fuzzy | Sistema de inferencia difusa                                            |
| NumPy        | Cálculo numérico y vectores                                             |
| Matplotlib   | Generación de gráficas experimentales                                   |
| SciPy        | Soporte matemático y científico                                         |
| NetworkX     | Soporte para estructuras de análisis si se requiere ampliar el proyecto |

---

## Instalación

### 1. Clonar o abrir el proyecto

Ubicarse en la carpeta del proyecto:

```bash
cd ~/SmarTextCB
```

### 2. Crear un entorno virtual

En Linux o macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

En Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Ejecución de la aplicación

Desde la raíz del proyecto:

```bash
python ui/main.py
```

Al iniciar, la aplicación cargará los recursos necesarios, incluyendo:

* vocabulario en español;
* datos del usuario;
* modelo de bigramas;
* modelo SOM.

La primera ejecución puede tardar un poco más porque algunos modelos deben entrenarse y guardarse en caché.

---

## Funcionamiento general

El flujo principal de SmartText es el siguiente:

1. El usuario escribe texto en la interfaz.
2. El sistema tokeniza el texto.
3. Cada palabra se compara con el vocabulario.
4. Si una palabra no aparece en el vocabulario, se buscan candidatos cercanos usando Levenshtein.
5. Las sugerencias se ordenan usando lógica difusa.
6. El sistema muestra las mejores correcciones.
7. También sugiere una posible siguiente palabra usando bigramas.
8. Si el usuario acepta o rechaza una corrección, el sistema guarda esa decisión.
9. Con el tiempo, SmartText adapta sus sugerencias al estilo del usuario.

---

## Módulos del backend

### `backend/corpus.py`

Este módulo se encarga de cargar el corpus en español usando `cess_esp` de NLTK. También construye el vocabulario, calcula frecuencias normalizadas y entrena el modelo de bigramas.

Funciones principales:

* `cargar_vocabulario()`
* `frecuencia_normalizada()`
* `ModeloBigramas`
* `sugerir_siguiente()`
* `guardar()`
* `cargar()`

El modelo de bigramas calcula la probabilidad de una palabra según la palabra anterior usando suavizado de Laplace.

---

### `backend/levenshtein.py`

Este módulo implementa la distancia de Levenshtein, que permite medir qué tan diferente es una palabra respecto a otra.

Se usa para encontrar posibles correcciones cuando una palabra no está en el vocabulario.

Funciones principales:

* `distancia_levenshtein()`
* `distancia_normalizada()`
* `buscar_candidatos()`

Ejemplo:

```txt
"haver" puede sugerir "haber"
"computdora" puede sugerir "computadora"
```

---

### `backend/fuzzy_ranker.py`

Este módulo utiliza lógica difusa para ordenar las sugerencias de corrección.

Entradas del sistema difuso:

* Distancia normalizada de Levenshtein.
* Frecuencia normalizada de la palabra en el corpus.

Salida:

* Relevancia de la sugerencia entre 0 y 1.

El sistema usa reglas tipo Mamdani, por ejemplo:

```txt
SI distancia es cercana Y frecuencia es alta
ENTONCES relevancia es muy alta
```

Funciones principales:

* `construir_sistema_difuso()`
* `calcular_relevancia()`
* `rankear_candidatos()`
* `graficar_membresias()`

---

### `backend/som_model.py`

Este módulo implementa un **Self-Organizing Map**, usado para agrupar palabras de forma topológica.

Cada palabra se transforma en un vector numérico usando características como:

* longitud;
* proporción de vocales;
* proporción de consonantes;
* distribución de caracteres.

Funciones principales:

* `palabra_a_vector()`
* `preparar_datos_som()`
* `entrenar_som()`
* `obtener_posicion_palabra()`
* `palabras_en_zona()`
* `graficar_som()`
* `guardar_som()`
* `cargar_som()`

El SOM permite visualizar cómo se agrupan palabras similares dentro del vocabulario.

---

### `backend/persistencia.py`

Este módulo guarda el historial local del usuario en un archivo JSON.

Registra:

* correcciones aceptadas;
* correcciones rechazadas;
* vocabulario personal;
* número de sesiones;
* estadísticas generales.

Funciones principales:

* `cargar_datos()`
* `guardar_datos()`
* `registrar_correccion_aceptada()`
* `registrar_correccion_rechazada()`
* `registrar_palabra_usada()`
* `obtener_correccion_preferida()`
* `estadisticas()`

El archivo generado es:

```txt
backend/usuario_data.json
```

Este archivo está excluido del repositorio porque contiene datos personales del usuario.

---

### `backend/engine.py`

Este es el motor central de SmartText. Integra todos los módulos anteriores y controla el procesamiento principal.

Responsabilidades:

* cargar vocabulario;
* cargar modelos;
* procesar texto;
* detectar errores;
* generar sugerencias;
* sugerir siguiente palabra;
* actualizar historial del usuario;
* aceptar o rechazar correcciones.

Clase principal:

```python
SmartTextEngine
```

Métodos importantes:

* `inicializar()`
* `procesar_texto()`
* `aceptar_correccion()`
* `rechazar_correccion()`
* `estadisticas_usuario()`

---

## Interfaz gráfica

La interfaz se encuentra en la carpeta `ui/`.

### `ui/main.py`

Es el punto de entrada de la aplicación Kivy.

Se encarga de:

* configurar la ventana;
* cargar el archivo KV;
* crear el `ScreenManager`;
* registrar las pantallas principales.

Pantallas registradas:

* `LoadingScreen`
* `EditorScreen`
* `StatsScreen`
* `SomScreen`

---

### `ui/screens.py`

Contiene la mayor parte de la interfaz gráfica.

Incluye:

* pantalla de carga;
* editor de texto;
* chips de sugerencias;
* subrayado de errores;
* sugerencia de siguiente palabra;
* botón de deshacer;
* pantalla de estadísticas;
* pantalla del mapa SOM;
* barra de navegación inferior.

---

### `ui/smarttext.kv`

Archivo KV simple para estilos globales de Kivy.

Define configuraciones base para:

* `Label`
* `Button`
* `TextInput`

---

## Módulo de experimentación

El archivo:

```txt
experiments/experimentos.py
```

permite ejecutar pruebas comparativas sobre los principales componentes del sistema.

Para ejecutar los experimentos:

```bash
python experiments/experimentos.py
```

Este módulo realiza cuatro experimentos:

### 1. Experimento Levenshtein

Compara diferentes umbrales de distancia:

* tiempo promedio;
* número de candidatos encontrados;
* precisión de recuperación de la palabra correcta.

Archivo generado:

```txt
experiments/experimento_levenshtein.png
```

---

### 2. Experimento de lógica difusa

Compara funciones de membresía:

* triangulares;
* trapezoidales.

Archivo generado:

```txt
experiments/experimento_fuzzy.png
```

---

### 3. Experimento SOM

Compara distintos tamaños de grid:

* error de cuantización;
* error topográfico;
* tiempo de entrenamiento.

Archivo generado:

```txt
experiments/experimento_som.png
```

---

### 4. Experimento N-gramas

Compara:

* bigramas;
* trigramas.

Métricas:

* precisión top-1;
* perplejidad;
* tiempo de entrenamiento.

Archivo generado:

```txt
experiments/experimento_ngramas.png
```

---

### Resumen de resultados

También se generan:

```txt
experiments/resumen_experimentos.png
experiments/resumen_resultados.txt
```

---

## Archivos generados automáticamente

Durante la ejecución, el sistema puede generar archivos de caché o resultados:

```txt
backend/modelo_bigramas.json
backend/som_model_pesos.npy
backend/som_model_palabras.json
backend/usuario_data.json
backend/mapa_som.png
backend/membresias.png
```

Estos archivos no son obligatorios para subir al repositorio, ya que pueden regenerarse.

Por eso algunos están incluidos en `.gitignore`.

---

## Archivo `.gitignore`

El proyecto excluye archivos que no deberían subirse al repositorio, como:

```txt
venv/
__pycache__/
*.pyc
backend/modelo_bigramas.json
backend/som_model_pesos.npy
backend/som_model_palabras.json
backend/usuario_data.json
.vscode/
*.log
.DS_Store
Thumbs.db
```

Esto ayuda a mantener el repositorio limpio y evita subir archivos pesados o datos privados del usuario.

---

## Ejemplo de uso

1. Abrir la aplicación:

```bash
python ui/main.py
```

2. Escribir una frase como:

```txt
la computdora funciona bien
```

3. SmartText detectará la palabra posiblemente incorrecta:

```txt
computdora
```

4. El sistema mostrará sugerencias como:

```txt
computadora
```

5. Si el usuario acepta la corrección, SmartText la guardará en su historial para mejorar futuras sugerencias.

---

## Consideraciones importantes

* La primera ejecución puede tardar más porque se descargan recursos de NLTK y se entrenan modelos.
* El sistema está enfocado principalmente en texto en español.
* El archivo `usuario_data.json` guarda información local del uso del usuario.
* El proyecto no requiere conexión a una base de datos externa.
* Los modelos generados pueden eliminarse y reconstruirse ejecutando nuevamente la aplicación.
* Para que la app funcione correctamente, el archivo de interfaz debe llamarse `screens.py`, ya que `main.py` lo importa con:

```python
from screens import LoadingScreen, EditorScreen, StatsScreen, SomScreen
```

---

## Posibles mejoras futuras

* Exportar la aplicación como APK para Android.
* Agregar soporte para más idiomas.
* Mejorar el modelo de sugerencia usando embeddings.
* Incorporar redes neuronales para corrección contextual.
* Optimizar búsqueda de candidatos en vocabularios grandes.
* Agregar modo oscuro/claro configurable.
* Guardar estadísticas más detalladas por sesión.
* Permitir importar textos largos desde archivos.
* Implementar evaluación automática con datasets externos.
