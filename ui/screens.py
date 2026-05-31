"""
screens.py — SmartText UI v2
Mejoras incluidas:
    - Chips táctiles más grandes (dp(48) alto) con feedback visual
    - Subrayado de errores en tiempo real sobre el TextInput
    - Animación de chips al aparecer (slide + fade)
    - Indicador visual: sugerencia del historial vs corpus
    - Botón deshacer última corrección
    - Haptic feedback (plyer, silencioso si no está disponible)
    - StatsScreen con indicador de precisión y palabras aprendidas del usuario
    - Pantalla de bienvenida con progreso entre sesiones
"""

import os
import sys
import threading
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.animation import Animation

# Haptic feedback — silencioso si plyer no está instalado
try:
    from plyer import vibrator
    HAS_VIBRATOR = True
except Exception:
    HAS_VIBRATOR = False

def haptic():
    if HAS_VIBRATOR:
        try: vibrator.vibrate(0.05)
        except Exception: pass

# ── Paleta ───────────────────────────────────────────────────────────────────
C = {
    'bg_dark':    get_color_from_hex('#0F0F14'),
    'bg_card':    get_color_from_hex('#1A1A24'),
    'bg_input':   get_color_from_hex('#12121A'),
    'accent':     get_color_from_hex('#7B61FF'),
    'accent2':    get_color_from_hex('#00D4AA'),
    'text_main':  get_color_from_hex('#F0EEFF'),
    'text_muted': get_color_from_hex('#7A7A9A'),
    'error':      get_color_from_hex('#FF6B6B'),
    'success':    get_color_from_hex('#00D4AA'),
    'border':     get_color_from_hex('#2A2A3A'),
    'personal':   get_color_from_hex('#FFB347'),  # color sugerencia personal
}

# Engine singleton
_engine = None
def get_engine():  return _engine
def set_engine(e): global _engine; _engine = e


# ── Widgets base ─────────────────────────────────────────────────────────────

class Card(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.padding = [dp(14), dp(10)]
        self.spacing = dp(8)
        with self.canvas.before:
            Color(*C['bg_card'])
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._u, size=self._u)
    def _u(self, *_): self._r.pos = self.pos; self._r.size = self.size


class AccentBtn(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ''
        self.background_color  = C['accent']
        self.color             = C['text_main']
        self.font_size         = dp(14)
        self.bold              = True
        self.size_hint_y       = None
        self.height            = dp(48)

    def on_press(self):
        haptic()
        Animation(background_color=[*C['accent2'][:3], 1], duration=0.08).start(self)

    def on_release(self):
        Animation(background_color=C['accent'], duration=0.2).start(self)


class GhostBtn(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ''
        self.background_color  = [0, 0, 0, 0]
        self.color             = C['accent']
        self.font_size         = dp(13)
        self.size_hint_y       = None
        self.height            = dp(48)
        with self.canvas.before:
            Color(*C['accent'])
            self._ln = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)),
                width=1)
        self.bind(pos=self._u, size=self._u)
    def _u(self, *_):
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(8))


class NavBar(BoxLayout):
    TABS = [('editor','✏','Editor'), ('stats','📊','Stats'), ('som','🗺','SOM')]

    def __init__(self, sm, current, **kw):
        super().__init__(**kw)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height      = dp(58)
        self.padding     = [dp(8), dp(6)]
        self.spacing     = dp(4)
        with self.canvas.before:
            Color(*C['bg_card'])
            self._r = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14), dp(14), 0, 0])
        self.bind(pos=self._u, size=self._u)

        for sname, icon, label in self.TABS:
            active = (sname == current)
            b = Button(
                text=f'{icon}\n{label}',
                background_normal='',
                background_color=C['accent'] if active else [0,0,0,0],
                color=C['text_main'] if active else C['text_muted'],
                font_size=dp(11), halign='center',
            )
            if sm:
                b.bind(on_press=lambda x, s=sname: (
                    haptic(), setattr(sm, 'current', s)))
            self.add_widget(b)

    def _u(self, *_): self._r.pos = self.pos; self._r.size = self.size


def make_header(title_text, subtitle=None):
    h = BoxLayout(orientation='vertical', size_hint_y=None,
                  height=dp(64) if subtitle else dp(56),
                  padding=[dp(20), dp(8)])
    with h.canvas.before:
        Color(*C['bg_card'])
        r = Rectangle(pos=h.pos, size=h.size)
    h.bind(pos=lambda *a: setattr(r,'pos',h.pos),
           size=lambda *a: setattr(r,'size',h.size))
    h.add_widget(Label(
        text=title_text, font_size=dp(20), bold=True,
        color=C['accent'], halign='left',
        text_size=(dp(300), None), size_hint_y=None, height=dp(28),
    ))
    if subtitle:
        h.add_widget(Label(
            text=subtitle, font_size=dp(11), color=C['text_muted'],
            halign='left', text_size=(dp(300), None),
            size_hint_y=None, height=dp(18),
        ))
    return h


# ── Chip de sugerencia animado ────────────────────────────────────────────────

class SuggestionChip(Button):
    """
    Chip táctil con:
      - Alto mínimo dp(48) para Android
      - Color según relevancia difusa
      - Indicador dorado si viene del historial personal
      - Animación de entrada slide+fade
    """
    def __init__(self, sugerencia, relevancia, es_personal=False,
                 on_accept=None, **kw):
        super().__init__(**kw)
        self.size_hint_x = None
        self.width       = dp(160)
        self.size_hint_y = None
        self.height      = dp(48)
        self.background_normal = ''
        self.font_size   = dp(13)
        self._sug        = sugerencia
        self._on_accept  = on_accept

        # Etiqueta con indicador personal
        star = '★ ' if es_personal else ''
        self.text = f'{star}{sugerencia}\n{relevancia:.2f}'

        # Color según relevancia
        if es_personal:
            bg = [*C['personal'][:3], 0.28]
            self.color = C['personal']
        elif relevancia > 0.7:
            bg = [*C['success'][:3], 0.25]
            self.color = C['success']
        elif relevancia > 0.4:
            bg = [*C['accent'][:3], 0.25]
            self.color = C['accent']
        else:
            bg = [*C['text_muted'][:3], 0.18]
            self.color = C['text_muted']

        self.background_color = bg

        # Animación entrada: empieza invisible y desplazado
        self.opacity = 0
        self.pos_hint = {}
        Clock.schedule_once(self._animate_in, 0.05)

    def _animate_in(self, *_):
        (Animation(opacity=1, duration=0.22) &
         Animation(height=dp(48), duration=0.18)).start(self)

    def on_press(self):
        haptic()
        Animation(opacity=0.6, duration=0.08).start(self)

    def on_release(self):
        Animation(opacity=1.0, duration=0.12).start(self)
        if self._on_accept:
            self._on_accept(self._sug)


# ── Overlay de subrayado de errores ──────────────────────────────────────────

class ErrorUnderlineOverlay(Widget):
    """
    Widget transparente que dibuja subrayados rojos ondulados
    debajo de las palabras con error en el TextInput.
    Funciona como overlay flotante encima del TextInput.
    """
    def __init__(self, text_input_ref, **kw):
        super().__init__(**kw)
        self._ti    = text_input_ref
        self._words = set()
        self.size_hint = (1, 1)

    def set_error_words(self, words: set):
        self._words = words
        self._draw()

    def _draw(self):
        self.canvas.clear()
        if not self._words or not self._ti._lines:
            return

        ti = self._ti
        with self.canvas:
            Color(*C['error'], 0.7)
            # Recorrer líneas visibles
            for line_idx, line_text in enumerate(ti._lines):
                y_line = (ti.top - ti.padding[1]
                          - (line_idx + 1) * (ti.line_height)
                          + ti.scroll_y)
                words_in_line = re.findall(r'\b\w+\b', line_text)
                x_cursor = ti.x + ti.padding[0]
                for word in words_in_line:
                    w_width = len(word) * ti._get_line_options()[0].get(
                        'font_size', dp(16)) * 0.55
                    if word.lower() in self._words:
                        # Línea ondulada simulada con segmentos
                        for seg in range(int(w_width / dp(4))):
                            sx = x_cursor + seg * dp(4)
                            sy = y_line - dp(2) + (dp(2) if seg % 2 == 0 else 0)
                            Line(points=[sx, sy, sx + dp(4), sy], width=1)
                    x_cursor += w_width + ti._get_line_options()[0].get(
                        'font_size', dp(16)) * 0.3

    def _get_line_options(self):
        # Fallback seguro
        return [{'font_size': dp(16)}]


# ── LoadingScreen ─────────────────────────────────────────────────────────────

class LoadingScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._progress = 0.0
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(40), spacing=dp(16))
        with root.canvas.before:
            Color(*C['bg_dark'])
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *a: setattr(bg,'pos',root.pos),
                  size=lambda *a: setattr(bg,'size',root.size))

        root.add_widget(Widget())

        # Logo animado
        logo = Label(
            text='SmartText', font_size=dp(48), bold=True,
            color=C['accent'], size_hint_y=None, height=dp(64),
        )
        root.add_widget(logo)
        # Animar logo al entrar
        Clock.schedule_once(lambda *_: (
            Animation(font_size=dp(52), duration=0.6).start(logo),
        ), 0.2)

        root.add_widget(Label(
            text='Corrector ortográfico inteligente\ncon IA adaptativa',
            font_size=dp(14), color=C['text_muted'],
            size_hint_y=None, height=dp(44), halign='center',
        ))

        # Badges de tecnologías
        badges = BoxLayout(size_hint_y=None, height=dp(28),
                           spacing=dp(6), padding=[dp(20), 0])
        for txt in ['Levenshtein', 'Fuzzy Logic', 'SOM', 'N-gramas']:
            b = Label(
                text=txt, font_size=dp(10), color=C['accent2'],
                size_hint_x=None, width=dp(80),
            )
            badges.add_widget(b)
        root.add_widget(badges)

        root.add_widget(Widget(size_hint_y=None, height=dp(20)))

        self.lbl_status = Label(
            text='Iniciando...', font_size=dp(13),
            color=C['text_muted'], size_hint_y=None, height=dp(24),
        )
        root.add_widget(self.lbl_status)

        # Barra de progreso
        pb = BoxLayout(size_hint_y=None, height=dp(6), padding=[dp(20), 0])
        self._pb = pb
        with pb.canvas:
            Color(*C['border'])
            self._pb_bg   = RoundedRectangle(pos=pb.pos, size=pb.size, radius=[dp(3)])
            Color(*C['accent'])
            self._pb_fill = RoundedRectangle(pos=pb.pos, size=(0, dp(6)), radius=[dp(3)])
        pb.bind(pos=self._upd_pb, size=self._upd_pb)
        root.add_widget(pb)

        root.add_widget(Widget())
        self.add_widget(root)

    def _upd_pb(self, *_):
        self._pb_bg.pos   = self._pb.pos
        self._pb_bg.size  = self._pb.size
        self._pb_fill.pos = self._pb.pos
        self._pb_fill.size = (self._pb.width * self._progress, dp(6))

    def on_enter(self):
        Clock.schedule_once(lambda *_: threading.Thread(
            target=self._load, daemon=True).start(), 0.5)

    def _load(self):
        from engine import SmartTextEngine
        engine = SmartTextEngine()
        steps = {
            'vocab':  ('Cargando vocabulario...', 0.25),
            'bigr':   ('Entrenando modelo de bigramas...', 0.55),
            'som':    ('Preparando SOM...', 0.80),
            'listo':  ('¡Listo!', 1.0),
        }

        def cb(msg):
            ml = msg.lower()
            for key, (txt, pct) in steps.items():
                if key in ml:
                    Clock.schedule_once(
                        lambda dt, t=txt, p=pct: self._set(t, p), 0)
                    return
            Clock.schedule_once(
                lambda dt, t=msg: self._set(t, min(self._progress+0.1, 0.95)), 0)

        engine.inicializar(callback_progreso=cb)
        set_engine(engine)
        Clock.schedule_once(lambda *_: self._set('¡Listo!', 1.0), 0)
        Clock.schedule_once(lambda *_: setattr(self.manager,'current','editor'), 0.9)

    def _set(self, msg, pct):
        self.lbl_status.text = msg
        self._progress = pct
        self._upd_pb()


# ── EditorScreen ──────────────────────────────────────────────────────────────

class EditorScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._debounce    = None
        self._undo_stack  = []   # [(texto_antes, error, correccion)]
        self._error_words = set()
        self._build()

    def _build(self):
        self._root = BoxLayout(orientation='vertical')
        with self._root.canvas.before:
            Color(*C['bg_dark'])
            bg = Rectangle(pos=self._root.pos, size=self._root.size)
        self._root.bind(
            pos=lambda *a: setattr(bg,'pos',self._root.pos),
            size=lambda *a: setattr(bg,'size',self._root.size))

        # ── Header ──
        hdr = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(20),dp(10)], spacing=dp(8))
        with hdr.canvas.before:
            Color(*C['bg_card'])
            hr = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda *a: setattr(hr,'pos',hdr.pos),
                 size=lambda *a: setattr(hr,'size',hdr.size))
        hdr.add_widget(Label(
            text='SmartText', font_size=dp(20), bold=True,
            color=C['accent'], size_hint_x=0.5, halign='left',
            text_size=(dp(180), None),
        ))

        # Indicador de precisión (se actualiza con el uso)
        self.lbl_precision = Label(
            text='precisión: —', font_size=dp(11),
            color=C['accent2'], size_hint_x=None, width=dp(100),
            halign='center',
        )
        hdr.add_widget(self.lbl_precision)

        self.lbl_words = Label(
            text='0 palabras', font_size=dp(11),
            color=C['text_muted'], size_hint_x=None, width=dp(70),
            halign='right',
        )
        hdr.add_widget(self.lbl_words)
        self._root.add_widget(hdr)

        # ── TextInput con FloatLayout para overlay ──
        float_wrap = FloatLayout(size_hint_y=0.38)

        self.txt = TextInput(
            hint_text='Escribe aquí...\nEl corrector analiza en tiempo real.',
            font_size=dp(16),
            foreground_color=C['text_main'],
            background_color=C['bg_card'],
            cursor_color=C['accent'],
            hint_text_color=C['text_muted'],
            multiline=True,
            padding=[dp(12), dp(10)],
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.txt.bind(text=self._on_text)
        float_wrap.add_widget(self.txt)

        # Overlay de subrayados (encima del TextInput, sin bloquear eventos)
        self._overlay = ErrorUnderlineOverlay(self.txt,
            size_hint=(1,1), pos_hint={'x':0,'y':0})
        float_wrap.add_widget(self._overlay)

        self._root.add_widget(float_wrap)

        # ── Leyenda de colores ──
        legend = BoxLayout(size_hint_y=None, height=dp(22),
                           padding=[dp(12), 0], spacing=dp(16))
        for color, txt in [
            (C['personal'], '★ historial'),
            (C['success'],  '● alta relevancia'),
            (C['accent'],   '● media'),
        ]:
            legend.add_widget(Label(
                text=txt, font_size=dp(10), color=color,
                halign='left', size_hint_x=None, width=dp(110),
            ))
        self._root.add_widget(legend)

        # ── Siguiente palabra ──
        self._root.add_widget(Label(
            text='  Siguiente palabra sugerida',
            font_size=dp(11), color=C['text_muted'],
            size_hint_y=None, height=dp(20), halign='left',
        ))
        sv_next = ScrollView(size_hint_y=None, height=dp(52), do_scroll_y=False)
        self.box_next = BoxLayout(
            orientation='horizontal', spacing=dp(6),
            size_hint_x=None, padding=[dp(12), dp(2)],
        )
        self.box_next.bind(minimum_width=self.box_next.setter('width'))
        sv_next.add_widget(self.box_next)
        self._root.add_widget(sv_next)

        # ── Correcciones ──
        corr_hdr = BoxLayout(size_hint_y=None, height=dp(26),
                             padding=[dp(12), 0], spacing=dp(8))
        corr_hdr.add_widget(Label(
            text='Correcciones sugeridas',
            font_size=dp(11), color=C['text_muted'], halign='left',
        ))
        # Botón deshacer
        self.btn_undo = Button(
            text='↩ Deshacer',
            background_normal='', background_color=[0,0,0,0],
            color=C['text_muted'], font_size=dp(11),
            size_hint_x=None, width=dp(90),
        )
        self.btn_undo.bind(on_press=self._undo)
        self.btn_undo.opacity = 0  # oculto hasta que hay algo que deshacer
        corr_hdr.add_widget(self.btn_undo)
        self._root.add_widget(corr_hdr)

        sv_corr = ScrollView(size_hint_y=0.28)
        self.box_corr = BoxLayout(
            orientation='vertical', spacing=dp(6),
            padding=[dp(12), dp(4)], size_hint_y=None,
        )
        self.box_corr.bind(minimum_height=self.box_corr.setter('height'))
        sv_corr.add_widget(self.box_corr)
        self._root.add_widget(sv_corr)

        # ── Botones acción ──
        btn_row = BoxLayout(size_hint_y=None, height=dp(60),
                            padding=[dp(12), dp(6)], spacing=dp(8))
        b1 = AccentBtn(text='Analizar')
        b1.bind(on_press=self._analizar)
        btn_row.add_widget(b1)
        b2 = GhostBtn(text='Limpiar', size_hint_x=None, width=dp(90))
        b2.bind(on_press=self._limpiar)
        btn_row.add_widget(b2)
        self._root.add_widget(btn_row)

        # Placeholder navbar
        self._root.add_widget(Widget(size_hint_y=None, height=dp(58)))
        self.add_widget(self._root)

    def on_enter(self):
        old = self._root.children[0]
        self._root.remove_widget(old)
        self._root.add_widget(NavBar(self.manager, 'editor'))
        self._actualizar_precision()

    def _actualizar_precision(self):
        engine = get_engine()
        if not engine: return
        stats = engine.estadisticas_usuario()
        total = stats.get('total_correcciones', 0)
        if total > 0:
            # Aproximar precisión: correcciones aceptadas / (aceptadas + rechazadas)
            aceptadas = total
            rechazadas = sum(
                len(v) for v in
                engine.datos_usuario.get('correcciones_rechazadas', {}).values()
            )
            pct = int(aceptadas / max(aceptadas + rechazadas, 1) * 100)
            self.lbl_precision.text = f'precisión: {pct}%'
        else:
            self.lbl_precision.text = 'precisión: —'

    def _on_text(self, inst, val):
        words = [w for w in val.split() if w]
        self.lbl_words.text = f'{len(words)} palabras'
        if self._debounce: self._debounce.cancel()
        self._debounce = Clock.schedule_once(self._analizar, 0.7)

    def _limpiar(self, *_):
        self.txt.text = ''
        self.box_corr.clear_widgets()
        self.box_next.clear_widgets()
        self._overlay.set_error_words(set())
        self._undo_stack.clear()
        self.btn_undo.opacity = 0

    def _analizar(self, *_):
        engine = get_engine()
        if not engine: return
        texto = self.txt.text.strip()
        if not texto:
            self.box_corr.clear_widgets()
            self.box_next.clear_widgets()
            self._overlay.set_error_words(set())
            return
        try:
            res = engine.procesar_texto(texto)
            Clock.schedule_once(lambda dt: self._render(res), 0)
        except Exception as e:
            print(f'[EditorScreen] Error análisis: {e}')

    def _render(self, res):
        errores = res.get('errores', {})

        # Actualizar overlay de subrayados
        self._error_words = set(errores.keys())
        self._overlay.set_error_words(self._error_words)

        # ── Siguiente palabra ──
        self.box_next.clear_widgets()
        for item in res.get('siguiente_palabra', [])[:5]:
            b = Button(
                text=item['palabra'],
                size_hint_x=None, width=dp(110),
                size_hint_y=None, height=dp(48),
                background_normal='',
                background_color=[*C['accent'][:3], 0.18],
                color=C['accent'], font_size=dp(13),
            )
            b.bind(on_press=lambda x, p=item['palabra']: (haptic(), self._insert(p)))
            # Animación entrada
            b.opacity = 0
            Clock.schedule_once(
                lambda dt, btn=b: Animation(opacity=1, duration=0.2).start(btn), 0.05)
            self.box_next.add_widget(b)

        # ── Correcciones ──
        self.box_corr.clear_widgets()

        if not errores:
            ok = Label(
                text='✓  Sin errores detectados',
                color=C['success'], font_size=dp(14),
                size_hint_y=None, height=dp(40),
            )
            ok.opacity = 0
            Animation(opacity=1, duration=0.3).start(ok)
            self.box_corr.add_widget(ok)
            return

        engine = get_engine()
        for palabra, sugs in errores.items():
            # Detectar si hay sugerencia preferida del historial
            preferida = None
            if engine:
                from persistencia import obtener_correccion_preferida
                preferida = obtener_correccion_preferida(
                    engine.datos_usuario, palabra)

            # Fila de error con palabra subrayada visualmente
            row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))
            row.add_widget(Label(
                text=f'✗  {palabra}', color=C['error'],
                font_size=dp(14), bold=True,
                size_hint_x=None, width=dp(140), halign='left',
            ))
            row.add_widget(Label(
                text='→', color=C['text_muted'],
                size_hint_x=None, width=dp(18),
            ))
            self.box_corr.add_widget(row)

            # Chips de sugerencias
            sv = ScrollView(size_hint_y=None, height=dp(56), do_scroll_y=False)
            cb = BoxLayout(
                orientation='horizontal', spacing=dp(8),
                size_hint_x=None, padding=[dp(2), dp(2)],
            )
            cb.bind(minimum_width=cb.setter('width'))

            for i, s in enumerate(sugs[:5]):
                es_personal = (s['sugerencia'] == preferida)
                chip = SuggestionChip(
                    sugerencia=s['sugerencia'],
                    relevancia=s['relevancia'],
                    es_personal=es_personal,
                    on_accept=lambda p, pe=palabra: self._aceptar(pe, p),
                )
                # Delay escalonado para animación en cascada
                chip.opacity = 0
                Clock.schedule_once(
                    lambda dt, c=chip: Animation(opacity=1, duration=0.2).start(c),
                    0.05 * (i + 1))
                cb.add_widget(chip)

            sv.add_widget(cb)
            self.box_corr.add_widget(sv)

            # Separador
            sep = Widget(size_hint_y=None, height=dp(1))
            with sep.canvas:
                Color(*C['border'])
                Rectangle(pos=sep.pos, size=(Window.width, dp(1)))
            self.box_corr.add_widget(sep)

    def _insert(self, palabra):
        t = self.txt.text
        self.txt.text = (t if t.endswith(' ') else t + ' ') + palabra + ' '

    def _aceptar(self, error, correccion):
        engine = get_engine()
        texto_antes = self.txt.text

        if engine:
            engine.aceptar_correccion(error, correccion)

        # Guardar en undo stack
        self._undo_stack.append((texto_antes, error, correccion))
        self.btn_undo.opacity = 1
        self.btn_undo.color = C['accent2']

        # Reemplazar en texto
        self.txt.text = re.sub(
            r'\b' + re.escape(error) + r'\b',
            correccion, self.txt.text, count=1,
        )

        # Actualizar precisión
        self._actualizar_precision()

    def _undo(self, *_):
        if not self._undo_stack: return
        haptic()
        texto_antes, error, correccion = self._undo_stack.pop()

        engine = get_engine()
        if engine:
            engine.rechazar_correccion(error, correccion)

        self.txt.text = texto_antes

        if not self._undo_stack:
            self.btn_undo.opacity = 0


# ── ErrorUnderlineOverlay (versión simplificada y funcional) ─────────────────

class ErrorUnderlineOverlay(Widget):
    """
    Dibuja líneas rojas debajo de palabras con error.
    Versión funcional sin depender de internals de TextInput.
    """
    def __init__(self, text_input_ref, **kw):
        super().__init__(**kw)
        self._ti    = text_input_ref
        self._words = set()

    def set_error_words(self, words: set):
        self._words = words
        self.canvas.clear()
        if not words: return

        ti = self._ti
        with self.canvas:
            Color(*C['error'], 0.65)
            for line_idx, line_text in enumerate(ti._lines):
                words_in_line = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', line_text)
                x_pos = ti.x + ti.padding[0]
                y_pos = (ti.top - ti.padding[1]
                         - (line_idx + 1) * ti.line_height
                         + ti.scroll_y - dp(2))

                for word in words_in_line:
                    char_w = ti.font_size * 0.58
                    w_px = len(word) * char_w
                    if word.lower() in self._words:
                        # Línea ondulada con segmentos alternados
                        x = x_pos
                        toggle = 0
                        while x < x_pos + w_px - dp(3):
                            y_seg = y_pos + (dp(2) if toggle % 2 == 0 else 0)
                            Line(points=[x, y_seg, x + dp(4), y_seg], width=1.2)
                            x += dp(4)
                            toggle += 1
                    x_pos += w_px + char_w * 0.6  # espacio entre palabras


# ── StatsScreen ───────────────────────────────────────────────────────────────

class StatsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        self._root = BoxLayout(orientation='vertical')
        with self._root.canvas.before:
            Color(*C['bg_dark'])
            bg = Rectangle(pos=self._root.pos, size=self._root.size)
        self._root.bind(
            pos=lambda *a: setattr(bg,'pos',self._root.pos),
            size=lambda *a: setattr(bg,'size',self._root.size))

        self._root.add_widget(make_header(
            'Análisis de escritura',
            subtitle='Estadísticas de aprendizaje adaptativo'))

        sv = ScrollView()
        self._content = BoxLayout(
            orientation='vertical', spacing=dp(12),
            padding=[dp(16), dp(12)], size_hint_y=None,
        )
        self._content.bind(minimum_height=self._content.setter('height'))
        sv.add_widget(self._content)
        self._root.add_widget(sv)

        btn_row = BoxLayout(size_hint_y=None, height=dp(60),
                            padding=[dp(16), dp(6)])
        b = AccentBtn(text='Actualizar estadísticas')
        b.bind(on_press=self._load)
        btn_row.add_widget(b)
        self._root.add_widget(btn_row)

        self._root.add_widget(Widget(size_hint_y=None, height=dp(58)))
        self.add_widget(self._root)

    def on_enter(self):
        old = self._root.children[0]
        self._root.remove_widget(old)
        self._root.add_widget(NavBar(self.manager, 'stats'))
        self._load()

    def _load(self, *_):
        self._content.clear_widgets()
        engine = get_engine()
        if not engine:
            self._content.add_widget(Label(
                text='Engine cargando...',
                color=C['text_muted'], size_hint_y=None, height=dp(40)))
            return

        stats  = engine.estadisticas_usuario()
        datos  = engine.datos_usuario

        # ── Grid métricas ──
        total_ac  = stats.get('total_correcciones', 0)
        rechazadas = sum(len(v) for v in
                         datos.get('correcciones_rechazadas', {}).values())
        precision  = (int(total_ac / max(total_ac + rechazadas, 1) * 100)
                      if total_ac > 0 else 0)

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(110))
        for titulo, valor, color in [
            ('Sesiones',         str(stats.get('sesiones',0)),           C['accent']),
            ('Correcciones',     str(total_ac),                          C['success']),
            ('Palabras aprendidas', str(stats.get('palabras_aprendidas',0)), C['accent2']),
            ('Precisión',        f'{precision}%',                        C['personal']),
        ]:
            c = Card(orientation='vertical')
            lv = Label(text=valor, font_size=dp(26), bold=True,
                       color=color, size_hint_y=None, height=dp(34))
            c.add_widget(lv)
            c.add_widget(Label(text=titulo, font_size=dp(10),
                               color=C['text_muted'], size_hint_y=None, height=dp(18)))
            # Animación de entrada
            lv.opacity = 0
            Animation(opacity=1, duration=0.4).start(lv)
            grid.add_widget(c)
        self._content.add_widget(grid)

        # ── Top palabras aprendidas del usuario ──
        vocab_usuario = datos.get('vocabulario_usuario', {})
        if vocab_usuario:
            self._content.add_widget(Label(
                text='Tus palabras más usadas',
                font_size=dp(13), bold=True, color=C['text_main'],
                size_hint_y=None, height=dp(30), halign='left'))

            top_palabras = sorted(vocab_usuario.items(),
                                  key=lambda x: x[1], reverse=True)[:8]
            palabras_row = BoxLayout(
                orientation='horizontal', spacing=dp(6),
                size_hint_y=None, height=dp(36), padding=[0, dp(2)])
            for palabra, conteo in top_palabras:
                chip = Label(
                    text=f'{palabra} ({conteo})',
                    font_size=dp(11), color=C['accent2'],
                    size_hint_x=None, width=dp(90),
                )
                palabras_row.add_widget(chip)
            self._content.add_widget(palabras_row)

        # ── Errores frecuentes ──
        self._content.add_widget(Label(
            text='Errores frecuentes',
            font_size=dp(13), bold=True, color=C['text_main'],
            size_hint_y=None, height=dp(30), halign='left'))

        errores = stats.get('errores_frecuentes', [])
        if errores:
            for i, e in enumerate(errores[:5]):
                row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
                row.add_widget(Label(
                    text=f'{i+1}.', color=C['text_muted'],
                    size_hint_x=None, width=dp(22), font_size=dp(13)))
                row.add_widget(Label(
                    text=e, color=C['error'], font_size=dp(14), halign='left'))
                self._content.add_widget(row)
        else:
            self._content.add_widget(Label(
                text='Sin errores registrados aún.',
                color=C['text_muted'], font_size=dp(13),
                size_hint_y=None, height=dp(34)))

        # ── Última sesión ──
        self._content.add_widget(Label(
            text=f"Última sesión: {stats.get('ultima_sesion','—')[:19]}",
            font_size=dp(11), color=C['text_muted'],
            size_hint_y=None, height=dp(24)))

        # ── Imagen funciones de membresía ──
        ruta = os.path.join(
            os.path.dirname(__file__), '..', 'backend', 'membresias.png')
        if os.path.exists(ruta):
            self._content.add_widget(Label(
                text='Funciones de membresía — lógica difusa',
                font_size=dp(12), bold=True, color=C['text_main'],
                size_hint_y=None, height=dp(28)))
            self._content.add_widget(KivyImage(
                source=ruta, size_hint_y=None,
                height=dp(190), allow_stretch=True))


# ── SomScreen ─────────────────────────────────────────────────────────────────

class SomScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        self._root = BoxLayout(orientation='vertical')
        with self._root.canvas.before:
            Color(*C['bg_dark'])
            bg = Rectangle(pos=self._root.pos, size=self._root.size)
        self._root.bind(
            pos=lambda *a: setattr(bg,'pos',self._root.pos),
            size=lambda *a: setattr(bg,'size',self._root.size))

        self._root.add_widget(make_header(
            'Mapa SOM — Vocabulario',
            subtitle='Clustering topológico de palabras en español'))

        self._root.add_widget(Label(
            text='Palabras similares aparecen juntas.\nZonas oscuras = fronteras entre clusters.',
            font_size=dp(12), color=C['text_muted'],
            size_hint_y=None, height=dp(36), halign='center'))

        sv = ScrollView()
        img_box = BoxLayout(orientation='vertical', padding=[dp(8)],
                            size_hint_y=None, height=dp(380))
        self.som_img = KivyImage(
            source='', size_hint_y=None, height=dp(340), allow_stretch=True)
        # Animación al cargar imagen
        self.som_img.opacity = 0
        img_box.add_widget(self.som_img)

        self.lbl_som = Label(
            text='Cargando mapa...', color=C['text_muted'],
            font_size=dp(13), size_hint_y=None, height=dp(32))
        img_box.add_widget(self.lbl_som)
        sv.add_widget(img_box)
        self._root.add_widget(sv)

        btn_row = BoxLayout(size_hint_y=None, height=dp(60),
                            padding=[dp(16), dp(6)])
        b = AccentBtn(text='Regenerar mapa SOM')
        b.bind(on_press=self._regenerar)
        btn_row.add_widget(b)
        self._root.add_widget(btn_row)

        self._root.add_widget(Widget(size_hint_y=None, height=dp(58)))
        self.add_widget(self._root)

    def on_enter(self):
        old = self._root.children[0]
        self._root.remove_widget(old)
        self._root.add_widget(NavBar(self.manager, 'som'))
        self._cargar_img()

    def _cargar_img(self):
        ruta = os.path.join(
            os.path.dirname(__file__), '..', 'backend', 'mapa_som.png')
        if os.path.exists(ruta):
            self.som_img.source = ruta
            self.som_img.reload()
            Animation(opacity=1, duration=0.5).start(self.som_img)
            self.lbl_som.text = 'Mapa cargado — zoom con pellizco'
        else:
            self.lbl_som.text = 'Sin mapa. Toca "Regenerar".'

    def _regenerar(self, *_):
        haptic()
        self.lbl_som.text = 'Generando mapa (~30s)...'
        Animation(opacity=0.3, duration=0.2).start(self.som_img)
        threading.Thread(target=self._gen_thread, daemon=True).start()

    def _gen_thread(self):
        try:
            from corpus import cargar_vocabulario
            from som_model import (preparar_datos_som, entrenar_som,
                                   graficar_som, guardar_som)
            vocab, freqs = cargar_vocabulario()
            palabras, X  = preparar_datos_som(vocab, freqs, min_freq=5, max_palabras=300)
            som = entrenar_som(X, grid_x=12, grid_y=12, n_iter=500)
            base    = os.path.join(os.path.dirname(__file__), '..', 'backend', 'som_model')
            ruta_img = os.path.join(os.path.dirname(__file__), '..', 'backend', 'mapa_som.png')
            graficar_som(som, palabras, X, guardar_en=ruta_img)
            guardar_som(som, palabras, base)
            Clock.schedule_once(lambda *_: self._cargar_img(), 0)
        except Exception as e:
            Clock.schedule_once(
                lambda *_, err=str(e): setattr(self.lbl_som,'text',f'Error: {err}'), 0)