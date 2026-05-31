"""
main.py — SmartText UI
Punto de entrada de la aplicación Kivy.

Cómo correr (desde la raíz del proyecto SmarText CB/):
    python ui/main.py
"""

import os
import sys

# Backend al path ANTES de cualquier import de kivy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Configuración de Kivy — DEBE ir antes de importar kivy.core
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.config import Config
Config.set('graphics', 'width',     '420')
Config.set('graphics', 'height',    '780')
Config.set('graphics', 'resizable', True)
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from screens import LoadingScreen, EditorScreen, StatsScreen, SomScreen

KV_PATH = os.path.join(os.path.dirname(__file__), 'smarttext.kv')
Builder.load_file(KV_PATH)


class SmartTextApp(App):
    def build(self):
        self.title = 'SmartText — Corrector Inteligente'
        Window.clearcolor = get_color_from_hex('#0F0F14')

        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(EditorScreen(name='editor'))
        sm.add_widget(StatsScreen(name='stats'))
        sm.add_widget(SomScreen(name='som'))
        sm.current = 'loading'
        return sm


if __name__ == '__main__':
    SmartTextApp().run()