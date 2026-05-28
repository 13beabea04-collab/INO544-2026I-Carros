#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector de Carros - Ridge Racer R4 Type-4 Edition (Python Codebase)
Asistente Universitario de Reconocimiento y Reporte Vehicular.
Soporta: Selección de fotos, análisis por lote, reportería en tiempo real y soporte API.
"""

import os
import sys
import json
import time
import base64
import threading
from datetime import datetime
import urllib.request
from io import BytesIO

# Tkinter and graphic imports
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Optional high-quality image processing packages
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    NUMPY_DISPONIBLE = False

try:
    import tensorflow as tf
    TENSORFLOW_DISPONIBLE = True
except ImportError:
    TENSORFLOW_DISPONIBLE = False

# Optional Gemini Direct SDK
try:
    import google.generativeai as genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

# Optional Camera capture via OpenCV
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."

def _parsear_rutas_drop(data):
    data = (data or "").strip()
    if not data:
        return []
    import re
    if data.startswith("{"):
        return [p.strip() for p in re.findall(r"\{([^}]+)\}", data)]
    return [p.strip() for p in data.split() if p.strip()]


# Theme Settings (Ridge Racer Type-4 Aesthetic)
COLOR_YELLOW = "#FFB800"      # Bright Neobrutalist R4 Yellow background
COLOR_DARK_BG = "#1A1A1A"     # Deep Charcoal
COLOR_PANEL_BG = "#121212"    # Underlay obsidian black
COLOR_WHITE = "#FFFFFF"
COLOR_ORANGE = "#FF5500"      # Retro Accent 1
COLOR_GREEN = "#66FF99"       # Success indicator
COLOR_RED = "#FF4444"         # Error / Danger
COLOR_TEXT_MUTED = "#888888"


class RetroButton(tk.Canvas):
    """Custom drawing Tkinter canvas mimicking Neobrutalist 3D-shadow Ridge Racer Buttons"""
    def __init__(self, parent, text, command=None, variant="primary", width=180, height=36, disabled=False, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.variant = variant
        self.disabled = disabled
        self.width = width
        self.height = height
        
        self.pressed = False
        self.hovered = False
        
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        self.redraw()
        
    def _on_press(self, event):
        if self.disabled: return
        self.pressed = True
        self.redraw()
        
    def _on_release(self, event):
        if self.disabled: return
        if self.pressed:
            self.pressed = False
            self.redraw()
            if self.command:
                self.command()
                
    def _on_enter(self, event):
        if self.disabled: return
        self.hovered = True
        self.redraw()
        
    def _on_leave(self, event):
        self.pressed = False
        self.hovered = False
        self.redraw()

    def set_state(self, disabled=False):
        self.disabled = disabled
        self.redraw()

    def redraw(self):
        self.delete("all")
        
        if self.disabled:
            bg_color = "#333333"
            text_color = "#666666"
            shadow_color = "none"
            indicator_color = "#444444"
        else:
            shadow_color = "#000000"
            if self.variant == "primary":
                bg_color = "#111111" if not self.hovered else "#2A2A2A"
                text_color = COLOR_ORANGE if self.pressed else COLOR_WHITE
                indicator_color = COLOR_ORANGE
            elif self.variant == "danger":
                bg_color = "#2D1B1B" if not self.hovered else "#4A1A1A"
                text_color = COLOR_RED
                indicator_color = COLOR_RED
            elif self.variant == "camera":
                bg_color = "#111111" if not self.hovered else "#222222"
                text_color = COLOR_WHITE
                indicator_color = COLOR_ORANGE
            else: # secondary
                bg_color = "#222222" if not self.hovered else "#333333"
                text_color = "#CCCCCC"
                indicator_color = "#888888"

        # Apply Neobrutalist offsets (translate 2px when pressed)
        offset = 2 if self.pressed else 0
        shadow_offset = 3 if not self.pressed and not self.disabled else 0

        # Draw shadows
        if shadow_offset > 0:
            self.create_rectangle(
                shadow_offset, shadow_offset, 
                self.width, self.height, 
                fill="#000000", outline=""
            )

        # Main Button Plate
        x1 = offset
        y1 = offset
        x2 = self.width - shadow_offset + offset
        y2 = self.height - shadow_offset + offset
        
        self.create_rectangle(
            x1, y1, x2, y2, 
            fill=bg_color, outline="#000000", width=2
        )
        
        # Inner text label
        self.create_text(
            15 + offset, (self.height - shadow_offset) // 2 + offset,
            text=self.text.upper(), fill=text_color,
            font=("Courier", 10, "bold"), anchor="w"
        )
        
        # Retro visual square detector in the right corner
        sq_size = 14
        sx1 = x2 - sq_size - 8
        sy1 = (self.height - shadow_offset) // 2 - sq_size // 2 + offset
        sx2 = x2 - 8
        sy2 = sy1 + sq_size
        
        self.create_rectangle(
            sx1, sy1, sx2, sy2, 
            fill=indicator_color, outline=COLOR_WHITE, width=1
        )


class VisualFrame(tk.LabelFrame):
    """Custom styled frame with double border outline for high-contrast neobrutalism"""
    def __init__(self, parent, text="", **kwargs):
        super().__init__(
            parent, 
            text=f"*{text.upper()}", 
            bg=COLOR_DARK_BG, 
            fg=COLOR_WHITE, 
            font=("Courier", 10, "bold"),
            bd=3, 
            relief="solid", 
            padx=8, 
            pady=8,
            **kwargs
        )


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("DETECTOR DE CARROS - RIDGE RACER EDITION (PYTHON SDK)")
        self.root.geometry("1100x720")
        self.root.configure(bg=COLOR_YELLOW)
        
        # State variables
        self.imagenes_lote = [] # list of dicts: {id, name, path, status, es_carro, certeza, desc}
        self.imagen_activa = None # dict
        self.indices_seleccionados = set()
        self.detectando_lote = False
        self.cancelar_lote = False
        self.camera_activa = False
        self.cam_cap = None
        
        # Local model state
        self.modelo_cargado = False
        self.umbral = 0.5
        self.cargar_umbral()
        self.cargar_modelo()
        
        # Initialize default items
        self.cargar_imagenes_demostracion()
        
        # Build UI layout
        self.setup_header()
        self.setup_grid()
        self.setup_footer()
        
        # Setup Drag and Drop functionality
        self.setup_drag_drop()
        
        # Start Clock loop
        self.update_clock()

    def update_clock(self):
        utc_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        self.clock_label.config(text=utc_now)
        self.root.after(1000, self.update_clock)

    def cargar_umbral(self):
        ruta = os.path.join(BASE_DIR, "umbral_optimo.json")
        if os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as f:
                    self.umbral = float(json.load(f).get("umbral", 0.5))
                print(f"Umbral de detección cargado: {self.umbral:.2f}")
            except (json.JSONDecodeError, TypeError, ValueError):
                self.umbral = 0.5
        else:
            self.umbral = 0.5

    def cargar_modelo(self):
        if not TENSORFLOW_DISPONIBLE:
            self.modelo_cargado = False
            print("AVISO: TensorFlow/Keras no está instalado en este sistema de Python.")
            return

        try:
            ruta_modelo = os.path.join(BASE_DIR, "modelo_carros.h5")
            if os.path.exists(ruta_modelo):
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
                self.modelo = tf.keras.models.load_model(ruta_modelo, compile=False)
                self.modelo_cargado = True
                print("Modelo Keras listo (.h5)")
            elif os.path.exists("modelo_carros.h5"):
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
                self.modelo = tf.keras.models.load_model("modelo_carros.h5", compile=False)
                self.modelo_cargado = True
                print("Modelo Keras listo (.h5) en ruta local")
            else:
                self.modelo_cargado = False
                print("No se encuentra el archivo 'modelo_carros.h5' en el directorio.")
        except Exception as e:
            self.modelo_cargado = False
            print(f"Error al inicializar cargado de red neuronal: {e}")

    def setup_header(self):
        header_bar = tk.Frame(self.root, bg=COLOR_YELLOW, height=70)
        header_bar.pack(fill="x", padx=10, pady=5)
        
        # Left side
        logo_frame = tk.Frame(header_bar, bg=COLOR_YELLOW)
        logo_frame.pack(side="left", fill="both")
        
        lbl_block = tk.Label(logo_frame, text="/*", bg=COLOR_DARK_BG, fg=COLOR_YELLOW, font=("Courier", 16, "bold"), width=3, relief="solid")
        lbl_block.pack(side="left", padx=(0,10))
        
        lbl_title_frame = tk.Frame(logo_frame, bg=COLOR_YELLOW)
        lbl_title_frame.pack(side="left")
        
        lbl_title = tk.Label(lbl_title_frame, text="SISTEMA DETECTOR DE CARROS", bg=COLOR_YELLOW, fg=COLOR_DARK_BG, font=("Helvetica", 14, "bold"))
        lbl_title.pack(anchor="w")
        lbl_sub = tk.Label(lbl_title_frame, text="R4 EDITION - ASISTENTE DE REPORTES UNIVERSITARIO", bg=COLOR_YELLOW, fg=COLOR_DARK_BG, font=("Courier", 9, "bold"))
        lbl_sub.pack(anchor="w")
        
        # Right side clock & core status
        right_frame = tk.Frame(header_bar, bg=COLOR_YELLOW)
        right_frame.pack(side="right", fill="y")
        
        self.clock_label = tk.Label(right_frame, text="...", bg="#FFFFFF", fg=COLOR_DARK_BG, font=("Courier", 10, "bold"), bd=1, relief="solid", padx=8)
        self.clock_label.pack(anchor="e", pady=(0,4))
        
        status_text = "MODELO: LOCAL (KERAS)" if self.modelo_cargado else "MODELO: SIMULACIÓN"
        status_color = COLOR_GREEN if self.modelo_cargado else COLOR_ORANGE
        status_banner = tk.Label(right_frame, text=status_text, bg=COLOR_DARK_BG, fg=status_color, font=("Courier", 9, "bold"), bd=1, relief="solid", padx=6)
        status_banner.pack(anchor="e")

        # Divider line
        div = tk.Frame(self.root, height=2, bg=COLOR_DARK_BG)
        div.pack(fill="x", padx=10, pady=(0, 10))

    def setup_grid(self):
        # Three main columns: Control Sidebar (left), Main Preview (center), List Explorer + Batch Action (right)
        grid_frame = tk.Frame(self.root, bg=COLOR_YELLOW)
        grid_frame.pack(fill="both", expand=True, padx=10)
        
        # 1. Sidebar Controls (Left)
        sidebar = tk.Frame(grid_frame, bg=COLOR_YELLOW, width=220)
        sidebar.pack(side="left", fill="both", padx=(0,5))
        sidebar.pack_propagate(False)
        
        self.setup_sidebar(sidebar)
        
        # 2. Main Preview Viewport (Center)
        center_viewport = tk.Frame(grid_frame, bg=COLOR_YELLOW)
        center_viewport.pack(side="left", fill="both", expand=True, padx=5)
        
        self.setup_center_viewport(center_viewport)
        
        # 3. Directory and Batch Controller (Right)
        right_sidebar = tk.Frame(grid_frame, bg=COLOR_YELLOW, width=280)
        right_sidebar.pack(side="left", fill="both", padx=(5,0))
        right_sidebar.pack_propagate(False)
        
        self.setup_right_sidebar(right_sidebar)

    def setup_sidebar(self, parent):
        # Selection Tools
        frame_tools = VisualFrame(parent, text="Captura")
        frame_tools.pack(fill="x", pady=(0,10))
        
        btn_cam = RetroButton(frame_tools, "Cámara en Vivo", command=self.toggle_camera, variant="camera", width=180)
        btn_cam.pack(pady=4)
        
        btn_file = RetroButton(frame_tools, "Cargar Fotos", command=self.importar_imagenes, variant="secondary", width=180)
        btn_file.pack(pady=4)
        
        btn_folder = RetroButton(frame_tools, "Cargar Carpeta", command=self.importar_carpeta, variant="secondary", width=180)
        btn_folder.pack(pady=4)
        
        btn_gallery_sidebar = RetroButton(frame_tools, "Ver Galería", command=self.abrir_vista_previa_galeria, variant="secondary", width=180)
        btn_gallery_sidebar.pack(pady=4)
        
        delim = tk.Frame(frame_tools, height=1, bg="#2A2A2A")
        delim.pack(fill="x", pady=6)
        
        self.btn_detect = RetroButton(frame_tools, "Detectar Carro", command=self.procesar_activo, variant="primary", width=180)
        self.btn_detect.pack(pady=4)
        
        btn_clear = RetroButton(frame_tools, "Limpiar Todo", command=self.limpiar_datos, variant="danger", width=180)
        btn_clear.pack(pady=4)
        
        # High Spec Badge (Vibe Graphic)
        frame_badge = tk.Frame(parent, bg=COLOR_DARK_BG, bd=2, relief="solid")
        frame_badge.pack(fill="both", expand=True)
        
        canvas_badge = tk.Canvas(frame_badge, bg=COLOR_PANEL_BG, highlightthickness=0)
        canvas_badge.pack(fill="both", expand=True, padx=5, pady=5)
        
        canvas_badge.create_text(10, 15, text="RIDGE RACER TYPE 4", fill=COLOR_ORANGE, font=("Courier", 8, "bold"), anchor="w")
        canvas_badge.create_text(10, 30, text="STAGE 4 ACTIVE", fill=COLOR_WHITE, font=("Courier", 10, "bold"), anchor="w")
        
        # Stripes
        canvas_badge.create_rectangle(10, 45, 180, 58, fill=COLOR_ORANGE, outline="")
        canvas_badge.create_rectangle(10, 62, 100, 70, fill=COLOR_WHITE, outline="")
        canvas_badge.create_rectangle(10, 74, 50, 77, fill=COLOR_TEXT_MUTED, outline="")
        
        engine_str = "LOCAL CONVOLUTIONAL (.H5)" if self.modelo_cargado else "GEMINI PREDICTIVE CHIP"
        canvas_badge.create_text(10, 100, text=f"SYSTEM POWERED BY\n{engine_str}", fill=COLOR_TEXT_MUTED, font=("Courier", 8, "bold"), anchor="w")

    def setup_center_viewport(self, parent):
        # Big Preview Visual Box
        self.frame_preview = VisualFrame(parent, text="Vista Previa")
        self.frame_preview.pack(fill="both", expand=True, pady=(0,10))
        
        # Image rendering canvas
        self.canvas_img = tk.Canvas(self.frame_preview, bg=COLOR_PANEL_BG, highlightthickness=1, highlightbackground="#333333")
        self.canvas_img.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Set drag and drop helper instruction on canvas
        self.canvas_img.create_text(
            150, 150, 
            text="[ SELECCIONE O SQUEEZE UNA IMAGEN ]\n\nPresione 'Cargar Fotos' o use\nlos ejemplos del explorador derecho.", 
            fill=COLOR_TEXT_MUTED, font=("Courier", 10, "bold"), justify="center", tags="placeholder"
        )
        self.canvas_img.bind("<Configure>", self.on_preview_resize)
        
        # Info details & report panel
        frame_report = VisualFrame(parent, text="Reporte de clasificación")
        frame_report.pack(fill="x")
        
        # Results horizontal card
        result_box = tk.Frame(frame_report, bg=COLOR_PANEL_BG, bd=1, relief="solid", padx=10, pady=10)
        result_box.pack(fill="x", pady=(0,8))
        
        lbl_res_title = tk.Label(result_box, text="CLASIFICACIÓN VEHICULAR:", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED, font=("Courier", 8, "bold"))
        lbl_res_title.grid(row=0, column=0, sticky="w")
        
        self.lbl_result_val = tk.Label(result_box, text="ESPERANDO DETECCIÓN", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED, font=("Courier", 14, "bold"))
        self.lbl_result_val.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2,4))
        
        lbl_cer_title = tk.Label(result_box, text="NIVEL DE CERTEZA:", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_MUTED, font=("Courier", 8, "bold"))
        lbl_cer_title.grid(row=2, column=0, sticky="w")
        
        self.lbl_prob_val = tk.Label(result_box, text="—%", bg=COLOR_PANEL_BG, fg=COLOR_WHITE, font=("Courier", 10, "bold"))
        self.lbl_prob_val.grid(row=2, column=1, sticky="w", padx=10)

        # Confidence Bar UI
        bar_frame = tk.Frame(result_box, bg="#222222", height=12, bd=1, relief="solid")
        bar_frame.grid(row=3, column=0, columnspan=3, sticky="we", pady=(6,0))
        result_box.grid_columnconfigure(2, weight=1)
        
        self.bar_fill = tk.Frame(bar_frame, bg=COLOR_TEXT_MUTED, width=0, height=10)
        self.bar_fill.pack(side="left", fill="y")
        
        # Explanation panel
        f_explain = tk.Frame(frame_report, bg="#1A1A1A", bd=1, relief="solid", padx=8, pady=8)
        f_explain.pack(fill="x")
        
        lbl_exp_header = tk.Label(f_explain, text="ANALISIS DEL MODELO AI:", bg="#1A1A1A", fg=COLOR_ORANGE, font=("Courier", 8, "bold"))
        lbl_exp_header.pack(anchor="w")
        
        self.txt_explain = tk.Label(
            f_explain, 
            text="No hay análisis disponible para esta imagen.\nSelecciona un coche y presiona 'Detectar Carro'.", 
            bg="#1A1A1A", fg="#DDDDDD", font=("Courier", 8, "bold"), justify="left", wraplength=480, anchor="w"
        )
        self.txt_explain.pack(anchor="w", fill="x", pady=4)

    def setup_right_sidebar(self, parent):
        # Simulating folder image system
        frame_explorer = VisualFrame(parent, text="Folder")
        frame_explorer.pack(fill="both", expand=True, pady=(0,10))
        
        lbl_exp_sub = tk.Label(frame_explorer, text="EXPLORADOR DE CARPETA LOCAL", bg=COLOR_DARK_BG, fg=COLOR_ORANGE, font=("Courier", 8, "bold"))
        lbl_exp_sub.pack(anchor="w", pady=(0,6))
        
        # Batch items controls (Select all/none)
        f_select = tk.Frame(frame_explorer, bg=COLOR_DARK_BG)
        f_select.pack(fill="x", pady=(0,6))
        
        btn_self_all = tk.Button(f_select, text="[✔] TODOS", bg="#222222", fg="#FFFFFF", font=("Courier", 8, "bold"), bd=1, relief="solid", command=self.seleccionar_todos, cursor="hand2")
        btn_self_all.pack(side="left", fill="x", expand=True, padx=(0,2))
        
        btn_self_none = tk.Button(f_select, text="[✖] NINGUNO", bg="#222222", fg="#FFFFFF", font=("Courier", 8, "bold"), bd=1, relief="solid", command=self.deseleccionar_todos, cursor="hand2")
        btn_self_none.pack(side="left", fill="x", expand=True, padx=(2,2))
        
        btn_gallery_explorer = tk.Button(f_select, text="🖼 GALERÍA", bg="#222222", fg=COLOR_GREEN, font=("Courier", 8, "bold"), bd=1, relief="solid", command=self.abrir_vista_previa_galeria, cursor="hand2")
        btn_gallery_explorer.pack(side="left", fill="x", expand=True, padx=(0,0))
        
        # Scrollable ListView containing elements
        list_container = tk.Frame(frame_explorer, bg=COLOR_PANEL_BG, bd=1, relief="solid")
        list_container.pack(fill="both", expand=True)
        
        # Pack Scrollbar FIRST so it is always visible on the right margin
        scrollbar = tk.Scrollbar(list_container, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        self.canvas_list = tk.Canvas(list_container, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.canvas_list.pack(side="left", fill="both", expand=True)
        
        # Symmetrically link scrollbar & list canvas
        scrollbar.config(command=self.canvas_list.yview)
        self.canvas_list.configure(yscrollcommand=lambda *args: [scrollbar.set(*args), getattr(self, "actualizar_explorer_visible", lambda: None)()])
        
        self.scroll_frame = tk.Frame(self.canvas_list, bg=COLOR_PANEL_BG)
        self.canvas_list.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        
        # Re-render explorer visible when configured (resizing, scrolling, etc)
        def _on_canvas_configure(e):
            try:
                self.canvas_list.configure(scrollregion=(0, 0, e.width, len(self.imagenes_lote) * 32))
                self.scroll_frame.configure(width=e.width)
            except Exception:
                pass
            getattr(self, "actualizar_explorer_visible", lambda: None)()
            
        self.canvas_list.bind("<Configure>", _on_canvas_configure)
        
        # Also bind mouse wheel directly on the list canvas so it works beautifully
        self.canvas_list.bind("<MouseWheel>", lambda e: [self.canvas_list.yview_scroll(int(-1*(e.delta/120)), "units"), getattr(self, "actualizar_explorer_visible", lambda: None)()])
        
        self.render_explorer_items()

        # Batch controller triggering list analysis
        self.frame_batch = VisualFrame(parent, text="Lote")
        self.frame_batch.pack(fill="x")
        
        self.btn_batch_run = RetroButton(self.frame_batch, "Detectar Seleccionadas", command=self.correr_procesamiento_lote, variant="primary", width=230)
        self.btn_batch_run.pack(pady=4)
        
        self.progress_label = tk.Label(self.frame_batch, text="PRECIOSO SISTEMA DE MULTI-HILOS", bg=COLOR_DARK_BG, fg=COLOR_TEXT_MUTED, font=("Courier", 8), justify="center")
        self.progress_label.pack(fill="x")

    def setup_footer(self):
        footer_div = tk.Frame(self.root, height=2, bg=COLOR_DARK_BG)
        footer_div.pack(fill="x", padx=10, pady=(10, 4))
        
        footer_bar = tk.Frame(self.root, bg=COLOR_YELLOW)
        footer_bar.pack(fill="x", padx=10, pady=(0, 10))
        
        # Configure button to change theme background color
        self.btn_theme_config = tk.Button(
            footer_bar, text="⚙ CONFIG", bg=COLOR_DARK_BG, fg=COLOR_YELLOW,
            font=("Courier", 8, "bold"), bd=1, relief="solid", cursor="hand2",
            padx=10, command=self.abrir_configuracion_fondo
        )
        self.btn_theme_config.pack(side="left", padx=(0, 10))
        
        lbl_nav = tk.Label(footer_bar, text="| DOBLE CLICK EN ELEMENTO: DETECCIÓN EXPRESS | SELECCIONE CHECKBOX: OPERACIÓN EN LOTE |", bg=COLOR_YELLOW, fg=COLOR_DARK_BG, font=("Courier", 8, "bold"))
        lbl_nav.pack(side="left")
        
        lbl_ver = tk.Label(footer_bar, text="R4 VEHICULAR DETECTOR SYSTEM v3.1", bg=COLOR_YELLOW, fg=COLOR_ORANGE, font=("Courier", 8, "bold"))
        lbl_ver.pack(side="right")

    def cambiar_color_fondo(self, nuevo_color):
        global COLOR_YELLOW
        old_color = COLOR_YELLOW
        COLOR_YELLOW = nuevo_color
        
        def traverse(widget):
            try:
                current_bg = widget.cget("bg")
                # Update any widget that has the old bg color or is specifically styled with yellow
                if current_bg in (old_color, "#FFB800") or "yellow" in str(current_bg).lower():
                    widget.configure(bg=nuevo_color)
            except Exception:
                pass
            
            try:
                current_fg = widget.cget("fg")
                # If foreground was yellow, update it for contrast or aesthetics
                if current_fg in (old_color, "#FFB800"):
                    if nuevo_color == COLOR_DARK_BG or nuevo_color == "#333333":
                        widget.configure(fg="#FF5500")
                    else:
                        widget.configure(fg=COLOR_DARK_BG)
            except Exception:
                pass
                
            for child in widget.winfo_children():
                traverse(child)
                
        self.root.configure(bg=nuevo_color)
        traverse(self.root)
        
        # Keep config button text matching the active background color
        try:
            self.btn_theme_config.configure(fg=nuevo_color if nuevo_color != COLOR_DARK_BG else "#FF5500")
        except Exception:
            pass

    def abrir_configuracion_fondo(self):
        config_win = tk.Toplevel(self.root)
        config_win.title("CONFIGURACIÓN DE COLOR DE FONDO")
        config_win.geometry("480x280")
        config_win.resizable(False, False)
        config_win.configure(bg=COLOR_DARK_BG)
        config_win.transient(self.root)
        config_win.grab_set()
        
        lbl_head = tk.Label(
            config_win, text="SELECCIONAR COLOR DE TEMA R4", 
            bg=COLOR_YELLOW if COLOR_YELLOW != COLOR_DARK_BG else COLOR_ORANGE,
            fg=COLOR_DARK_BG, font=("Courier", 11, "bold"), pady=8
        )
        lbl_head.pack(fill="x", pady=(0, 15))
        
        color_frame = tk.Frame(config_win, bg=COLOR_DARK_BG)
        color_frame.pack(padx=20, pady=5)
        
        colores = [
            ("AMARILLO R4", "#FFB800"),
            ("NARANJA NEBULA", "#FF5500"),
            ("CYBER ROJO", "#FF4444"),
            ("FROST AZUL", "#00A2E8"),
            ("NEO CELESTE", "#00DFFF"),
            ("ESMERALDA", "#00CC66"),
            ("MÁGICO PÚRPURA", "#8A2BE2"),
            ("CARBÓN OSCURO", "#333333")
        ]
        
        def pick_color(hex_color, label_widget=lbl_head):
            self.cambiar_color_fondo(hex_color)
            try:
                label_widget.config(bg=hex_color if hex_color != COLOR_DARK_BG else COLOR_ORANGE)
            except Exception:
                pass
        
        for idx, (name, hex_color) in enumerate(colores):
            r = idx // 4
            c = idx % 4
            
            btn_col = tk.Button(
                color_frame, text=name, bg=hex_color, fg="#FFFFFF" if hex_color not in ("#FFB800", "#00DFFF") else "#111111",
                font=("Courier", 8, "bold"), width=12, height=2, bd=2, relief="raised", cursor="hand2",
                command=lambda hc=hex_color: pick_color(hc)
            )
            btn_col.grid(row=r, column=c, padx=5, pady=5)
            
        btn_close = tk.Button(
            config_win, text="CERRAR VENTANA", bg="#222222", fg=COLOR_WHITE,
            font=("Courier", 9, "bold"), bd=1, relief="solid", cursor="hand2",
            padx=10, pady=5, command=config_win.destroy
        )
        btn_close.pack(side="bottom", pady=15)

    def setup_drag_drop(self):
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop_archivos)
            self.frame_preview.drop_target_register(DND_FILES)
            self.frame_preview.dnd_bind("<<Drop>>", self._on_drop_archivos)
            self.canvas_img.drop_target_register(DND_FILES)
            self.canvas_img.dnd_bind("<<Drop>>", self._on_drop_archivos)
            self.canvas_img.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            self.canvas_img.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            print("[INFO] tkinterdnd2 cargado exitosamente.")
            return
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import windnd
                windnd.hook_dropfiles(self.canvas_img, func=self._on_drop_windnd)
                windnd.hook_dropfiles(self.frame_preview, func=self._on_drop_windnd)
                print("[INFO] windnd cargado exitosamente como fallback.")
            except Exception:
                print("[WARNING] No se cargó ninguna biblioteca de drag & drop (instale windnd o tkinterdnd2).")
                pass

    def _on_drop_windnd(self, rutas):
        for r in rutas:
            ruta = str(r).strip().strip('"')
            if os.path.isfile(ruta):
                self._cargar_archivo_arrastrado(ruta)
                break

    def _on_drop_archivos(self, event):
        self._restaurar_borde_drop()
        data = event.data
        for ruta in _parsear_rutas_drop(data):
            if os.path.isfile(ruta):
                self._cargar_archivo_arrastrado(ruta)
                break

    def _on_drag_enter(self, event):
        self.canvas_img.config(highlightbackground=COLOR_ORANGE, highlightthickness=3)

    def _on_drag_leave(self, event):
        self._restaurar_borde_drop()

    def _restaurar_borde_drop(self):
        self.canvas_img.config(highlightbackground="#333333", highlightthickness=1)

    def _cargar_archivo_arrastrado(self, p):
        if not os.path.isfile(p): return
        name = os.path.basename(p)
        item_id = f"file-{int(time.time())}-{name}"
        
        try:
            with open(p, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            item = {
                "id": item_id,
                "name": name,
                "url": f"data:image/jpeg;base64,{encoded_string}",
                "path": p,
                "status": "idle",
                "es_carro": None,
                "certeza": None,
                "desc": None
            }
            self.imagenes_lote.append(item)
            self.indices_seleccionados.add(item_id)
            self.imagen_activa = item
            
            self.camera_activa = False
            self.render_explorer_items()
            self.mostrar_imagen_activa()
        except Exception as ex:
            print(f"Error al cargar archivo arrastrado: {ex}")

    # ================= FILES AND SEED DATA MANAGEMENT =================
    def cargar_imagenes_demostracion(self):
        demos = [
            ("R4_GT_Spec_Red.jpg", "https://images.unsplash.com/photo-1542282088-fe8426682b8f?w=640&auto=format&fit=crop&q=80"),
            ("Classic_Retro_Yellow.jpg", "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=640&auto=format&fit=crop&q=80"),
            ("Highway_Rush_Hour.jpg", "https://images.unsplash.com/photo-1506015391300-4802dc74de2e?w=640&auto=format&fit=crop&q=80"),
            ("Retro_Coffee_Cup.jpg", "https://images.unsplash.com/photo-1507133750040-4a8f57021571?w=640&auto=format&fit=crop&q=80"),
            ("Dorsal_Forest_Path.jpg", "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=640&auto=format&fit=crop&q=80")
        ]
        
        for i, (name, url) in enumerate(demos):
            item_id = f"demo-{i}"
            item = {
                "id": item_id,
                "name": name,
                "url": url,
                "path": None, # will download on demand or run local
                "status": "idle",
                "es_carro": None,
                "certeza": None,
                "desc": None
            }
            self.imagenes_lote.append(item)
            # Default select the first 3
            if i < 3:
                self.indices_seleccionados.add(item_id)
                
        self.imagen_activa = self.imagenes_lote[0]

    def render_explorer_items(self):
        total = len(self.imagenes_lote)
        
        if not hasattr(self, "explorer_widgets_cache"):
            self.explorer_widgets_cache = {}
            
        for widget in self.scroll_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass
        self.explorer_widgets_cache.clear()
        
        item_height = 32
        alto_contenido = total * item_height
        
        try:
            canvas_w = max(self.canvas_list.winfo_width(), 200)
            self.scroll_frame.configure(width=canvas_w, height=alto_contenido)
            self.canvas_list.configure(scrollregion=(0, 0, canvas_w, alto_contenido))
        except Exception:
            pass
            
        self.actualizar_explorer_visible()

    def actualizar_explorer_visible(self):
        total = len(self.imagenes_lote)
        if total == 0:
            if hasattr(self, "explorer_widgets_cache"):
                for cache in self.explorer_widgets_cache.values():
                    try:
                        cache["frame"].destroy()
                    except Exception:
                        pass
                self.explorer_widgets_cache.clear()
            return
            
        item_height = 32
        
        try:
            scroll_y = self.canvas_list.canvasy(0)
            viewport_h = max(self.canvas_list.winfo_height(), 100)
        except Exception:
            return
            
        i0 = max(0, int(scroll_y // item_height) - 4)
        i1 = min(total, int((scroll_y + viewport_h) // item_height) + 5)
        visibles = set(range(i0, i1))
        
        if not hasattr(self, "explorer_widgets_cache"):
            self.explorer_widgets_cache = {}
            
        for idx in list(self.explorer_widgets_cache.keys()):
            if idx not in visibles:
                try:
                    self.explorer_widgets_cache[idx]["frame"].destroy()
                except Exception:
                    pass
                del self.explorer_widgets_cache[idx]
                
        for idx in visibles:
            if idx not in self.explorer_widgets_cache:
                self._crear_fila_explorer_virtual(idx, item_height)

    def _crear_fila_explorer_virtual(self, idx, item_height):
        if idx >= len(self.imagenes_lote): return
        item = self.imagenes_lote[idx]
        item_id = item["id"]
        y_pos = idx * item_height
        
        is_selected = item_id in self.indices_seleccionados
        is_active = self.imagen_activa and self.imagen_activa["id"] == item_id
        
        bg_color = "#2E1606" if is_active else ("#222222" if is_selected else COLOR_PANEL_BG)
        
        row_frame = tk.Frame(self.scroll_frame, bg=bg_color, bd=1, relief="solid")
        row_frame.place(x=2, y=y_pos + 1, relwidth=1.0, width=-10, height=item_height - 2)
        
        chk_char = "▣" if is_selected else "▢"
        chk_color = COLOR_ORANGE if is_selected else COLOR_TEXT_MUTED
        btn_chk = tk.Button(
            row_frame, text=chk_char, bg=bg_color, fg=chk_color, 
            font=("Courier", 10, "bold"), bd=0, activebackground=bg_color,
            command=lambda i=item_id: self.toggle_seleccion_item(i), cursor="hand2"
        )
        btn_chk.pack(side="left", padx=4)
        
        text_color = COLOR_WHITE if is_active else "#BBBBBB"
        lbl_item = tk.Label(row_frame, text=item["name"], bg=bg_color, fg=text_color, font=("Courier", 8, "bold"), anchor="w", cursor="hand2")
        lbl_item.pack(side="left", fill="x", expand=True, padx=4)
        
        lbl_item.bind("<Button-1>", lambda e, it=item: self.inspeccionar_item(it))
        lbl_item.bind("<Double-Button-1>", lambda e, it=item: self.express_classify(it))
        
        state_label = tk.Label(row_frame, text="", bg=bg_color, width=2)
        state_label.pack(side="right", padx=4)
        
        if item["status"] == "success":
            icon_color = COLOR_GREEN if item["es_carro"] else COLOR_RED
            state_label.config(text="●", fg=icon_color)
        elif item["status"] == "loading":
            state_label.config(text="○", fg=COLOR_ORANGE)
        elif item["status"] == "error":
            state_label.config(text="▲", fg=COLOR_RED)
            
        btn_del = tk.Button(
            row_frame, text="✖", bg=bg_color, fg=COLOR_RED if is_active else "#555555",
            font=("Courier", 8), bd=0, activebackground=bg_color,
            command=lambda i=item_id: self.remover_item(i), cursor="hand2"
        )
        btn_del.pack(side="right", padx=2)
        
        # Bind mouse wheel to allow scrolling flawlessly anywhere over the rows
        def _on_wheel(e):
            self.canvas_list.yview_scroll(int(-1 * (e.delta / 120)), "units")
            self.actualizar_explorer_visible()
            
        row_frame.bind("<MouseWheel>", _on_wheel)
        btn_chk.bind("<MouseWheel>", _on_wheel)
        lbl_item.bind("<MouseWheel>", _on_wheel)
        state_label.bind("<MouseWheel>", _on_wheel)
        btn_del.bind("<MouseWheel>", _on_wheel)
        
        self.explorer_widgets_cache[idx] = {
            "frame": row_frame,
            "btn_chk": btn_chk,
            "lbl_item": lbl_item,
            "state_label": state_label,
            "btn_del": btn_del,
            "item_id": item_id
        }

    def render_single_explorer_item(self, item_id):
        if not hasattr(self, "explorer_widgets_cache"): return
        for idx, cache in self.explorer_widgets_cache.items():
            if cache.get("item_id") == item_id:
                item = next((x for x in self.imagenes_lote if x["id"] == item_id), None)
                if not item: return
                
                is_selected = item_id in self.indices_seleccionados
                is_active = self.imagen_activa and self.imagen_activa["id"] == item_id
                bg_color = "#2E1606" if is_active else ("#222222" if is_selected else COLOR_PANEL_BG)
                
                try:
                    cache["frame"].config(bg=bg_color)
                    
                    chk_char = "▣" if is_selected else "▢"
                    chk_color = COLOR_ORANGE if is_selected else COLOR_TEXT_MUTED
                    cache["btn_chk"].config(text=chk_char, bg=bg_color, fg=chk_color, activebackground=bg_color)
                    
                    text_color = COLOR_WHITE if is_active else "#BBBBBB"
                    cache["lbl_item"].config(bg=bg_color, fg=text_color)
                    
                    state_lbl = cache["state_label"]
                    state_lbl.config(bg=bg_color)
                    if item["status"] == "success":
                        icon_color = COLOR_GREEN if item["es_carro"] else COLOR_RED
                        state_lbl.config(text="●", fg=icon_color)
                    elif item["status"] == "loading":
                        state_lbl.config(text="○", fg=COLOR_ORANGE)
                    elif item["status"] == "error":
                        state_lbl.config(text="▲", fg=COLOR_RED)
                    else:
                        state_lbl.config(text="")
                        
                    cache["btn_del"].config(bg=bg_color, fg=COLOR_RED if is_active else "#555555", activebackground=bg_color)
                except Exception as update_err:
                    print(f"Error updating single widget item: {update_err}")
                break

    def toggle_seleccion_item(self, item_id):
        if item_id in self.indices_seleccionados:
            self.indices_seleccionados.remove(item_id)
        else:
            self.indices_seleccionados.add(item_id)
        self.render_single_explorer_item(item_id)

    def seleccionar_todos(self):
        for item in self.imagenes_lote:
            self.indices_seleccionados.add(item["id"])
        # Instant performance-safe caching refresh
        if hasattr(self, "explorer_widgets_cache"):
            for idx, cache in self.explorer_widgets_cache.items():
                self.render_single_explorer_item(cache["item_id"])

    def deseleccionar_todos(self):
        self.indices_seleccionados.clear()
        # Instant performance-safe caching refresh
        if hasattr(self, "explorer_widgets_cache"):
            for idx, cache in self.explorer_widgets_cache.items():
                self.render_single_explorer_item(cache["item_id"])

    def remover_item(self, item_id):
        self.imagenes_lote = [x for x in self.imagenes_lote if x["id"] != item_id]
        if item_id in self.indices_seleccionados:
            self.indices_seleccionados.remove(item_id)
            
        if self.imagen_activa and self.imagen_activa["id"] == item_id:
            if self.imagenes_lote:
                self.imagen_activa = self.imagenes_lote[0]
            else:
                self.imagen_activa = None
                
        self.render_explorer_items()
        self.mostrar_imagen_activa()

    def abrir_vista_previa_galeria(self):
        if not self.imagenes_lote:
            messagebox.showinfo("Carpeta Vacía", "No hay imágenes en el lote para previsualizar.")
            return
            
        gallery_win = tk.Toplevel(self.root)
        gallery_win.title("VISTA PREVIA DE TODAS LAS IMÁGENES")
        gallery_win.geometry("820x620")
        gallery_win.configure(bg=COLOR_DARK_BG)
        
        banner = tk.Frame(gallery_win, bg=COLOR_YELLOW, height=45)
        banner.pack(fill="x")
        lbl_win_title = tk.Label(banner, text="GALLERY PORTFOLIO - VISTA PREVIA DETALLADA", bg=COLOR_YELLOW, fg=COLOR_DARK_BG, font=("Courier", 11, "bold"))
        lbl_win_title.pack(side="left", padx=10, pady=10)
        
        container = tk.Frame(gallery_win, bg=COLOR_DARK_BG)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(container, bg=COLOR_PANEL_BG, highlightthickness=1, highlightbackground="#333333")
        canvas.pack(side="left", fill="both", expand=True)
        
        scroll = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scroll.set)
        
        grid_frame = tk.Frame(canvas, bg=COLOR_PANEL_BG)
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        
        def on_conf(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        grid_frame.bind("<Configure>", on_conf)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Setup high performance worker queue
        from queue import Queue
        img_queue = Queue()
        
        def _on_close():
            # Sentinel values to shut down workers safely
            for _ in range(3):
                img_queue.put(None)
            canvas.unbind_all("<MouseWheel>")
            gallery_win.destroy()
            
        gallery_win.protocol("WM_DELETE_WINDOW", _on_close)
  
        columns = 4
        if not hasattr(self, "gallery_images_refs"):
            self.gallery_images_refs = {}
        
        def load_thumb(item, label):
            try:
                img = None
                raw_url = item["url"]
                
                if raw_url.startswith("data:"):
                    meta, b64_raw = raw_url.split(",", 1)
                    img_data = base64.b64decode(b64_raw)
                    img = Image.open(BytesIO(img_data))
                elif raw_url.startswith("http"):
                    if item.get("path") and os.path.exists(item["path"]):
                        img = Image.open(item["path"])
                    else:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        req = urllib.request.Request(raw_url, headers=headers)
                        with urllib.request.urlopen(req) as response:
                            img_bytes = response.read()
                        img = Image.open(BytesIO(img_bytes))
                elif item.get("path") and os.path.exists(item["path"]):
                    img = Image.open(item["path"])
                    
                if img and PIL_AVAILABLE:
                    img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image=img)
                    
                    # Store photo to prevent garbage collection
                    self.gallery_images_refs[item["id"]] = photo
                    
                    def update_label_image():
                        try:
                            if label.winfo_exists():
                                label.config(image=photo, text="", width=120, height=120)
                                label.image = photo
                        except Exception:
                            pass
                            
                    label.after(0, update_label_image)
            except Exception as e:
                print(f"Error loading thumb for gallery preview: {e}")
                
        def queue_worker():
            while True:
                task = img_queue.get()
                if task is None:
                    break
                t_item, t_label = task
                load_thumb(t_item, t_label)
                img_queue.task_done()
                
        # Fire exactly 3 background worker threads
        for _ in range(3):
            threading.Thread(target=queue_worker, daemon=True).start()
                
        for index, item in enumerate(self.imagenes_lote):
            r = index // columns
            c = index % columns
            
            card = tk.Frame(grid_frame, bg="#1E1E1E", bd=1, relief="solid", padx=5, pady=5)
            card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            
            lbl_title = tk.Label(card, text=item["name"][:14], bg="#1E1E1E", fg=COLOR_WHITE, font=("Courier", 8, "bold"))
            lbl_title.pack(anchor="w", pady=(0, 4))
            
            lbl_img = tk.Label(card, text="Cargando...", bg="#111111", width=14, height=5, fg=COLOR_TEXT_MUTED)
            lbl_img.pack()
            
            status_text = "Sin anal."
            status_color = COLOR_TEXT_MUTED
            if item["status"] == "success":
                status_text = "Coche" if item["es_carro"] else "No coche"
                status_color = COLOR_GREEN if item["es_carro"] else COLOR_RED
                if item["certeza"] is not None:
                    status_text += f"\n({item['certeza']*100:.1f}%)"
            elif item["status"] == "loading":
                status_text = "Analizando..."
                status_color = COLOR_ORANGE
            elif item["status"] == "error":
                status_text = "Falla"
                status_color = COLOR_RED
                
            lbl_status = tk.Label(card, text=status_text, bg="#1E1E1E", fg=status_color, font=("Courier", 8, "bold"))
            lbl_status.pack(pady=3)
            
            def make_select_command(target_item):
                return lambda: [self.inspeccionar_item(target_item), gallery_win.destroy()]
                
            btn_select = tk.Button(card, text="SELECCIONAR", bg=COLOR_DARK_BG, fg=COLOR_ORANGE, font=("Courier", 8, "bold"), bd=1, relief="ridge", command=make_select_command(item))
            btn_select.pack(fill="x", pady=(2, 0))
            
            img_queue.put((item, lbl_img))

    def inspeccionar_item(self, item):
        self.camera_activa = False
        prev_active = self.imagen_activa
        self.imagen_activa = item
        
        # Performance-safe instant swap of active selection styles
        if prev_active:
            self.render_single_explorer_item(prev_active["id"])
        if item:
            self.render_single_explorer_item(item["id"])
            
        self.mostrar_imagen_activa()

    def express_classify(self, item):
        self.inspeccionar_item(item)
        self.procesar_activo()

    # ================= WEBCAM / CAPTURE AND IMPORT METHODS =================
    def toggle_camera(self):
        if self.camera_activa:
            self.close_camera()
        else:
            self.start_camera()

    def start_camera(self):
        if not OPENCV_AVAILABLE:
            messagebox.showerror("Error de Cámara", "OpenCV ('opencv-python') no está disponible. Por favor, instálalo usando:\npip install opencv-python")
            return
            
        self.cam_cap = cv2.VideoCapture(0)
        if not self.cam_cap.isOpened():
            messagebox.showerror("Error de Cámara", "No se detectó ningún dispositivo de video o webcam activo.")
            self.cam_cap = None
            return
            
        self.camera_activa = True
        self.imagen_activa = None
        self.canvas_img.delete("all")
        self.render_camera_frame()

    def render_camera_frame(self):
        if not self.camera_activa or not self.cam_cap:
            return
            
        ret, frame = self.cam_cap.read()
        if ret:
            # Flip horizontally for natural mirror feel
            frame = cv2.flip(frame, 1)
            
            # Convert OpenCV BGR to RGB
            cv2_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.last_camera_frame = cv2_rgb # preserve for capture
            
            # Draw on canvas
            if PIL_AVAILABLE:
                pil_img = Image.fromarray(cv2_rgb)
                
                # Resize keeping proportion to match frame
                canvas_w = max(self.canvas_img.winfo_width(), 100)
                canvas_h = max(self.canvas_img.winfo_height(), 100)
                pil_img.thumbnail((canvas_w, canvas_h))
                
                photo = ImageTk.PhotoImage(image=pil_img)
                self.tk_active_photo = photo # protect garbage collector
                
                self.canvas_img.create_image(canvas_w // 2, canvas_h // 2, image=photo, anchor="center")
                # Overlaid UI Frame tag
                self.canvas_img.create_rectangle(15, 15, 175, 40, fill="#FF5500", outline="#000000", width=1)
                self.canvas_img.create_text(25, 27, text="VISTA EN VIVO (OPENCV)", fill=COLOR_WHITE, font=("Courier", 8, "bold"), anchor="w")
                
        # Re-queue screen update
        self.root.after(30, self.render_camera_frame)

    def close_camera(self):
        self.camera_activa = False
        if self.cam_cap:
            self.cam_cap.release()
            self.cam_cap = None
        self.mostrar_imagen_activa()

    def capturar_camara(self):
        if not self.camera_activa or not hasattr(self, "last_camera_frame"):
            return
            
        try:
            pil_img = Image.fromarray(self.last_camera_frame)
            
            # Create base64 buffer or path
            buffered = BytesIO()
            pil_img.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Build item
            item_id = f"capture-{int(time.time())}"
            item = {
                "id": item_id,
                "name": f"captura_{int(time.time())}.jpg",
                "url": f"data:image/jpeg;base64,{img_b64}",
                "path": None,
                "status": "idle",
                "es_carro": None,
                "certeza": None,
                "desc": None
            }
            
            self.imagenes_lote.insert(0, item)
            self.indices_seleccionados.add(item_id)
            self.imagen_activa = item
            
            self.close_camera()
            self.render_explorer_items()
            self.mostrar_imagen_activa()
            
        except Exception as e:
            messagebox.showerror("Error de Captura", f"Ocurrió un error al procesar el fotograma capturado: {e}")

    def importar_imagenes(self):
        ficheros = filedialog.askopenfilenames(
            title="Importar Imágenes de Autos",
            filetypes=[("Archivos de Imagen", "*.jpg *.jpeg *.png *.webp *.gif")]
        )
        if not ficheros: return
        
        for p in ficheros:
            name = os.path.basename(p)
            item_id = f"file-{int(time.time())}-{name}"
            
            # Load and encode standard file
            try:
                with open(p, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                item = {
                    "id": item_id,
                    "name": name,
                    "url": f"data:image/jpeg;base64,{encoded_string}",
                    "path": p,
                    "status": "idle",
                    "es_carro": None,
                    "certeza": None,
                    "desc": None
                }
                self.imagenes_lote.append(item)
                self.indices_seleccionados.add(item_id)
                self.imagen_activa = item
            except Exception as ex:
                print(f"Error al cargar archivo local {name}: {ex}")
                
        self.camera_activa = False
        self.render_explorer_items()
        self.mostrar_imagen_activa()

    def importar_carpeta(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta para Análisis")
        if not folder: return
        
        valid_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")
        count = 0
        
        for name in os.listdir(folder):
            if name.lower().endswith(valid_extensions):
                full_path = os.path.join(folder, name)
                item_id = f"file-{int(time.time())}-{name}"
                
                try:
                    with open(full_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        
                    item = {
                        "id": item_id,
                        "name": name,
                        "url": f"data:image/jpeg;base64,{encoded_string}",
                        "path": full_path,
                        "status": "idle",
                        "es_carro": None,
                        "certeza": None,
                        "desc": None
                    }
                    self.imagenes_lote.append(item)
                    self.indices_seleccionados.add(item_id)
                    count += 1
                except Exception as ex:
                    print(f"No se pudo cargar {name}: {ex}")
                    
        if count > 0:
            self.camera_activa = False
            self.imagen_activa = self.imagenes_lote[-count] # point to first loaded in folder
            self.render_explorer_items()
            self.mostrar_imagen_activa()
            messagebox.showinfo("Importación Completada", f"Se cargaron de manera exitosa {count} imágenes vehiculares.")

    def limpiar_datos(self):
        self.close_camera()
        self.imagenes_lote = []
        self.indices_seleccionados.clear()
        self.imagen_activa = None
        self.canvas_img.delete("all")
        self.on_preview_resize(None)
        
        # Reset reports
        self.lbl_result_val.config(text="SIN IMAGEN", fg=COLOR_TEXT_MUTED)
        self.lbl_prob_val.config(text="—%")
        self.txt_explain.config(text="Ninguna imagen cargada.")
        self.bar_fill.pack_forget()
        self.render_explorer_items()

    # ================= IMAGE RENDERING =================
    def on_preview_resize(self, event):
        if not self.camera_activa:
            self.mostrar_imagen_activa()

    def mostrar_imagen_activa(self):
        self.canvas_img.delete("all")
        
        if self.camera_activa:
            return
            
        if not self.imagen_activa:
            # Render visual box instructions
            cw = max(self.canvas_img.winfo_width(), 300)
            ch = max(self.canvas_img.winfo_height(), 300)
            self.canvas_img.create_text(
                cw // 2, ch // 2, 
                text="[ SIN DISPOSITIVOS U HOJAS ACTIVAS ]\n\nPresione 'Cargar Fotos' o haga clic\nen sus archivos de la derecha.",
                fill=COLOR_TEXT_MUTED, font=("Courier", 10, "bold"), justify="center"
            )
            return
            
        # Draw Image loaded from base64, URL or disk
        try:
            img = None
            raw_url = self.imagen_activa["url"]
            
            if raw_url.startswith("data:"):
                # Decode Base64 data url
                meta, b64_raw = raw_url.split(",", 1)
                img_data = base64.b64decode(b64_raw)
                img = Image.open(BytesIO(img_data))
            elif raw_url.startswith("http"):
                # URL Download
                if self.imagen_activa["path"] and os.path.exists(self.imagen_activa["path"]):
                    img = Image.open(self.imagen_activa["path"])
                else:
                    self.canvas_img.create_text(
                        self.canvas_img.winfo_width() // 2, self.canvas_img.winfo_height() // 2,
                        text="DESCARGANDO MUESTRA DESDE UNSPLASH...",
                        fill=COLOR_ORANGE, font=("Courier", 10, "bold")
                    )
                    self.root.update()
                    # Safe thread download
                    headers = {"User-Agent": "Mozilla/5.0"}
                    req = urllib.request.Request(raw_url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        img_bytes = response.read()
                    
                    img = Image.open(BytesIO(img_bytes))
                    # Cache standard path temp file
                    temp_dir = os.path.join(os.path.expanduser("~"), ".r4_detector_cache")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_cache_path = os.path.join(temp_dir, f"{self.imagen_activa['id']}.jpg")
                    img.save(temp_cache_path, "JPEG")
                    self.imagen_activa["path"] = temp_cache_path
            
            if img and PIL_AVAILABLE:
                canvas_w = max(self.canvas_img.winfo_width(), 100)
                canvas_h = max(self.canvas_img.winfo_height(), 100)
                
                # Thumbnail helper preserving ratio
                img.thumbnail((canvas_w - 20, canvas_h - 20))
                
                photo = ImageTk.PhotoImage(image=img)
                self.tk_active_photo = photo # keep reference safe
                
                self.canvas_img.create_image(canvas_w // 2, canvas_h // 2, image=photo, anchor="center")
                
                # Upper Tag specs Overlay
                self.canvas_img.create_rectangle(15, 15, 195, 40, fill="#121212", outline="#333333", width=1)
                self.canvas_img.create_text(25, 27, text=f"FICHERO: {self.imagen_activa['name'].upper()}", fill=COLOR_ORANGE, font=("Courier", 8, "bold"), anchor="w")
                
            self.actualizar_reporte()
            
        except Exception as err:
            cw = max(self.canvas_img.winfo_width(), 300)
            ch = max(self.canvas_img.winfo_height(), 300)
            self.canvas_img.create_text(
                cw // 2, ch // 2,
                text=f"ERROR AL RENDERIZAR FOTO:\n{err}",
                fill=COLOR_RED, font=("Courier", 9, "bold"), justify="center"
            )

    def actualizar_reporte(self):
        item = self.imagen_activa
        if not item: return
        
        # Sync simple outputs matching the exact active item properties
        if item["status"] == "idle":
            self.lbl_result_val.config(text="ESPERANDO CLASIFICACIÓN", fg=COLOR_TEXT_MUTED)
            self.lbl_prob_val.config(text="—%")
            self.txt_explain.config(text="Presiona 'Detectar Carro' para clasificar este vehículo.")
            self.bar_fill.pack_forget()
        elif item["status"] == "loading":
            self.lbl_result_val.config(text="ANALIZANDO EN SERVIDOR AI...", fg=COLOR_ORANGE)
            self.lbl_prob_val.config(text="PROCESANDO")
            self.bar_fill.pack_forget()
        elif item["status"] == "error":
            self.lbl_result_val.config(text="¡FALLA DEL COPROCESADOR!", fg=COLOR_RED)
            self.lbl_prob_val.config(text="ERROR")
            self.txt_explain.config(text=item["desc"] or "Fallo de conexión o límites de API redundantes.")
            self.bar_fill.pack_forget()
        elif item["status"] == "success":
            name_lbl = "ES UN COCHE" if item["es_carro"] else "NO ES UN COCHE"
            lbl_color = COLOR_GREEN if item["es_carro"] else COLOR_RED
            self.lbl_result_val.config(text=name_lbl.upper(), fg=lbl_color)
            
            cert = item["certeza"] or 0.0
            self.lbl_prob_val.config(text=f"{cert * 100:.2f}%")
            
            # Fill bar meter width
            self.bar_fill.pack(side="left", fill="y")
            tot_w = 400
            self.bar_fill.config(width=int(tot_w * cert), bg=lbl_color)
            
            # Display translation text
            self.txt_explain.config(text=item["desc"] or "No se recuperaron comentarios descriptivos.")

    # ================= CLASS CAR DETECT LOGIC VIA LOCAL MODEL OR FALLBACK =================
    def query_model_for_car(self, item):
        """Processes a single payload invoking the local TensorFlow model or falling back if not available"""
        raw_url = item["url"]
        img = None
        
        try:
            if raw_url.startswith("data:"):
                # Decode Base64 data url
                meta, b64_raw = raw_url.split(",", 1)
                img_data = base64.b64decode(b64_raw)
                img = Image.open(BytesIO(img_data))
            elif raw_url.startswith("http"):
                # Download or load from path cache
                if item["path"] and os.path.exists(item["path"]):
                    img = Image.open(item["path"])
                else:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    req = urllib.request.Request(raw_url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        img_bytes = response.read()
                    img = Image.open(BytesIO(img_bytes))
            elif item["path"] and os.path.exists(item["path"]):
                img = Image.open(item["path"])
            
            if img is None:
                raise ValueError("No se pudo cargar la imagen")

            # Convert to RGB and resize to (224, 224)
            img_rgb = img.convert("RGB")
            img_resized = img_rgb.resize((224, 224), Image.Resampling.LANCZOS)
            
            # If TensorFlow and model is loaded, run local prediction
            if self.modelo_cargado and TENSORFLOW_DISPONIBLE and NUMPY_DISPONIBLE:
                arr = np.array(img_resized, dtype=np.float32) / 255.0
                img_array = np.expand_dims(arr, axis=0) # shape (1, 224, 224, 3)
                
                # Predict
                valor_crudo = float(self.modelo.predict(img_array, verbose=0)[0][0])
                es_carro = valor_crudo >= self.umbral
                probabilidad = valor_crudo if es_carro else (1.0 - valor_crudo)
                certeza = valor_crudo # raw probability
                
                desc = (
                    f"Análisis local convolucional (Keras). "
                    f"Se detectó un vehículo con confianza del {valor_crudo*100:.2f}% "
                    f"(Umbral: {self.umbral})"
                ) if es_carro else (
                    f"Análisis local convolucional (Keras). "
                    f"No parece ser un vehículo (confianza de coche: {valor_crudo*100:.2f}%, "
                    f"Umbral: {self.umbral})"
                )
                
                return {
                    "es_carro": es_carro,
                    "probabilidad": certeza,
                    "descripcion_modelo": desc
                }
            
            # Fallback to simulation if model not loaded
            h = sum(ord(c) for c in item["name"])
            valor_simulado = 0.89 if h % 2 == 0 else 0.12
            es_carro_sim = valor_simulado >= self.umbral
            
            desc_sim = (
                f"Simulando red neuronal (Modelo local ausente). "
                f"Resultado positivo para coche con {valor_simulado*100:.0f}%"
            ) if es_carro_sim else (
                f"Simulando red neuronal (Modelo local ausente). "
                f"Resultado negativo para coche con {valor_simulado*100:.0f}% de probabilidad"
            )
            
            print("[INFO] Fallback o Simulación utilizada en la detección")
            
            return {
                "es_carro": es_carro_sim,
                "probabilidad": valor_simulado,
                "descripcion_modelo": desc_sim
            }

        except Exception as e:
            print(f"[ERROR] Falló el procesamiento del modelo local o de red: {e}")
            raise e

    def procesar_activo(self):
        if not self.imagen_activa:
            messagebox.showwarning("Sin Selección", "Por favor selecciona primero un objeto automotor de la lista.")
            return
            
        if self.imagen_activa["status"] == "loading":
            return # Block double concurrent runs on same item
            
        self.imagen_activa["status"] = "loading"
        self.actualizar_reporte()
        self.render_explorer_items()
        self.btn_detect.set_state(disabled=True)
        
        # Thread out call to avoid Tkinter UI freezing
        def worker():
            try:
                res = self.query_model_for_car(self.imagen_activa)
                self.imagen_activa["es_carro"] = res["es_carro"]
                self.imagen_activa["certeza"] = res["probabilidad"]
                self.imagen_activa["desc"] = res["descripcion_modelo"]
                self.imagen_activa["status"] = "success"
                
            except Exception as e:
                self.imagen_activa["status"] = "error"
                self.imagen_activa["desc"] = f"Error al procesar: {e}"
                
            finally:
                self.root.after(0, self.finalizar_llamado_activo)
                
        threading.Thread(target=worker, daemon=True).start()

    def finalizar_llamado_activo(self):
        self.btn_detect.set_state(disabled=False)
        self.actualizar_reporte()
        self.render_explorer_items()

    # ================= BATCH DETECTOR SEQUENCING LOOP =================
    def correr_procesamiento_lote(self):
        if self.detectando_lote:
            # Act as cancel button
            self.cancelar_lote = True
            return
            
        rec_ids = list(self.indices_seleccionados)
        if not rec_ids:
            messagebox.showwarning("Selección Vacía", "Por favor selecciona algunas fotos marcando sus casillas [▢] antes de correr el lote.")
            return
            
        self.detectando_lote = True
        self.cancelar_lote = False
        self.btn_batch_run.text = "CANCELAR LOTE"
        self.btn_batch_run.redraw()
        
        # Threaded batch sequencer loop
        def batch_worker():
            total = len(rec_ids)
            for idx, target_id in enumerate(rec_ids):
                if self.cancelar_lote: break
                
                # Fetch matching item
                item = next((x for x in self.imagenes_lote if x["id"] == target_id), None)
                if not item: continue
                
                # Set element loading
                item["status"] = "loading"
                self.root.after(0, lambda tid=target_id: self.render_single_explorer_item(tid))
                
                self.root.after(0, lambda idx=idx, name=item['name']: self.progress_label.config(text=f"PROCESANDO {idx+1}/{total}: {name.upper()}", fg=COLOR_ORANGE))
                
                try:
                    res = self.query_model_for_car(item)
                    item["es_carro"] = res["es_carro"]
                    item["certeza"] = res["probabilidad"]
                    item["desc"] = res["descripcion_modelo"]
                    item["status"] = "success"
                    
                except Exception as ex:
                    item["status"] = "error"
                    item["desc"] = f"Error: {ex}"
                    
                # Dynamic performance delay: 0.01s for big batches, 0.2s for small ones
                wait_time = 0.01 if total > 5 else 0.2
                time.sleep(wait_time)
                self.root.after(0, lambda tid=target_id: self.render_single_explorer_item(tid))
                
            # Finish work callback
            self.root.after(0, self.finalizar_llamado_lote)
            
        threading.Thread(target=batch_worker, daemon=True).start()

    def finalizar_llamado_lote(self):
        self.detectando_lote = False
        self.btn_batch_run.text = "DETECTAR SELECCIONADAS"
        self.btn_batch_run.redraw()
        
        # Calculate totals
        batch_items = [x for x in self.imagenes_lote if x["id"] in self.indices_seleccionados]
        success_items = [x for x in batch_items if x["status"] == "success"]
        total_processed = len(success_items)
        
        if total_processed > 0:
            cars_count = sum(1 for x in success_items if x["es_carro"])
            not_cars_count = total_processed - cars_count
            pct_cars = (cars_count / total_processed) * 100
            
            # Show grand verdict
            verdict_text = f"VEREDICTO LOTE: {pct_cars:.1f}% TRÁFICO"
            status_color = COLOR_GREEN if pct_cars >= 50.0 else COLOR_YELLOW
            
            self.lbl_result_val.config(text=verdict_text, fg=status_color)
            self.lbl_prob_val.config(text=f"{cars_count}/{total_processed} COCHES")
            
            explain_text = (
                f"★★ VEREDICTO DE ANÁLISIS EN LOTE (COMPLETADO) ★★\n\n"
                f"• Total de archivos procesados exitosamente: {total_processed} de {len(batch_items)} seleccionados.\n"
                f"• Presencia de tráfico vehicular: {cars_count} coches ({pct_cars:.1f}%).\n"
                f"• Elementos descartados (no vehículos): {not_cars_count} ({100.0 - pct_cars:.1f}%).\n\n"
                f"Haz clic en cualquier imagen del explorador derecho para ver sus resultados de análisis individuales."
            )
            self.txt_explain.config(text=explain_text)
            
            # Fill confidence bar indicator
            self.bar_fill.pack(side="left", fill="y")
            tot_w = 400
            self.bar_fill.config(width=int(tot_w * (cars_count / total_processed)), bg=status_color)
            
            self.progress_label.config(text=f"LOTE TERMINADO: DETECTADOS {cars_count} COCHES ({pct_cars:.1f}%)", fg=COLOR_GREEN)
        else:
            self.progress_label.config(text="LOTE TERMINADO SIN PROCESADOS EXITOSOS", fg=COLOR_YELLOW)
            
        # Select first processed, update view
        if batch_items:
            self.imagen_activa = batch_items[0]
            self.mostrar_imagen_activa()
            self.actualizar_explorer_visible()


# Standalone program boot
if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD
        tk_root = TkinterDnD.Tk()
    except ImportError:
        tk_root = tk.Tk()
    app_instance = App(tk_root)
    tk_root.mainloop()