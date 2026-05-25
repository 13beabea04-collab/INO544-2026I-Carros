# ==============================================
# DETECTOR DE CARROS - PROYECTO UNIVERSITARIO
# ==============================================

import json
import os
import re
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import tensorflow as tf

from transformaciones_imagen import procesar_imagen_pil, procesar_imagen_seleccionada

CARPETA_CAPTURAS = "capturas"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_UI = os.path.join(BASE_DIR, "UI")
ICONO_TITULO = os.path.join(CARPETA_UI, "wheel.png")
ICONO_VENTANA = os.path.join(CARPETA_UI, "wheel2.jpg")

TEMA_CLARO = {
    "bg": "#f4f4f5",
    "surface": "#ffffff",
    "borde": "#e4e4e7",
    "texto": "#18181b",
    "texto_suave": "#71717a",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_active": "#1e40af",
    "secundario": "#f4f4f5",
    "secundario_hover": "#e4e4e7",
    "secundario_active": "#d4d4d8",
    "deshabilitado_bg": "#f4f4f5",
    "deshabilitado_fg": "#a1a1aa",
    "exito": "#16a34a",
    "error": "#dc2626",
    "borde_primary": "#2563eb",
    "borde_secondary": "#6366f1",
    "borde_danger": "#dc2626",
    "borde_camera": "#7c3aed",
    "borde_seleccion": "#06b6d4",
    "luna_fg": "#52525b",
    "luna_hover": "#18181b",
}

TEMA_OSCURO = {
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "borde": "#2d3348",
    "texto": "#f4f4f5",
    "texto_suave": "#a1a1aa",
    "accent": "#3b82f6",
    "accent_hover": "#60a5fa",
    "accent_active": "#2563eb",
    "secundario": "#252936",
    "secundario_hover": "#32384a",
    "secundario_active": "#3f4660",
    "deshabilitado_bg": "#1a1d27",
    "deshabilitado_fg": "#52525b",
    "exito": "#4ade80",
    "error": "#f87171",
    "borde_primary": "#3b82f6",
    "borde_secondary": "#818cf8",
    "borde_danger": "#f87171",
    "borde_camera": "#a78bfa",
    "borde_seleccion": "#22d3ee",
    "luna_fg": "#fbbf24",
    "luna_hover": "#fde68a",
}

FAMILIA = "Segoe UI" if sys.platform == "win32" else "Helvetica Neue"
FONT_BODY = (FAMILIA, 10)
FONT_SMALL = (FAMILIA, 9)
FONT_TITLE = (FAMILIA, 22, "bold")
FONT_SUBTITLE = (FAMILIA, 11)
FONT_BTN = (FAMILIA, 10)
FONT_RESULT = (FAMILIA, 17, "bold")
FONT_LUNA = (FAMILIA, 18)

EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
TEXTO_ARRASTRAR = "Arrastra una imagen aquí"
TEXTO_ARRASTRAR_SUB = "JPG · PNG · JPEG · BMP · GIF · WEBP"
TEXTO_SIN_IMAGEN = "No hay imagen seleccionada"


def _parsear_rutas_drop(data):
    """Interpreta rutas desde un evento de arrastre (tkinterdnd2)."""
    data = (data or "").strip()
    if not data:
        return []
    if data.startswith("{"):
        return [p.strip() for p in re.findall(r"\{([^}]+)\}", data)]
    return [p.strip() for p in data.split() if p.strip()]


def _es_archivo_imagen(ruta):
    return os.path.isfile(ruta) and ruta.lower().endswith(EXTENSIONES_IMAGEN)


def crear_ventana_raiz():
    try:
        from tkinterdnd2 import TkinterDnD

        return TkinterDnD.Tk()
    except ImportError:
        return tk.Tk()


def _cargar_icono(ruta, tamano):
    if not os.path.exists(ruta):
        return None
    img = Image.open(ruta).convert("RGBA")
    img.thumbnail(tamano, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)


class BotonMinimal(tk.Frame):
    """Boton con borde de color, feedback hover/clic y estado seleccionado."""

    VARIANTES = {
        "primary": "borde_primary",
        "secondary": "borde_secondary",
        "danger": "borde_danger",
        "camera": "borde_camera",
    }

    def __init__(
        self,
        parent,
        text,
        command=None,
        variant="primary",
        ancho=22,
        deshabilitado=False,
        tema=None,
    ):
        self._tema = tema or TEMA_CLARO
        self._command = command
        self._variant = variant
        self._deshabilitado = deshabilitado
        self._presionado = False
        self._seleccionado = False
        self._borde_key = self.VARIANTES.get(variant, "borde_secondary")

        borde = self._tema[self._borde_key]
        super().__init__(parent, bg=borde, padx=2, pady=2)

        colores = self._paleta("normal")
        self._inner = tk.Label(
            self,
            text=text,
            font=FONT_BTN,
            width=ancho,
            pady=10,
            cursor="arrow" if deshabilitado else "hand2",
            **colores,
        )
        self._inner.pack(fill="both", expand=True)

        if not deshabilitado:
            for w in (self, self._inner):
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)
                w.bind("<ButtonPress-1>", self._on_press)
                w.bind("<ButtonRelease-1>", self._on_release)

    def set_tema(self, tema):
        self._tema = tema
        self._actualizar_borde()
        if not self._deshabilitado:
            self._aplicar_estado("normal" if not self._presionado else "hover")

    def _actualizar_borde(self):
        if self._seleccionado:
            color = self._tema["borde_seleccion"]
            self.configure(bg=color, padx=3, pady=3)
        else:
            self.configure(bg=self._tema[self._borde_key], padx=2, pady=2)

    def set_seleccionado(self, activo):
        self._seleccionado = activo
        self._actualizar_borde()

    def _paleta(self, estado):
        t = self._tema
        if self._deshabilitado:
            return {"bg": t["deshabilitado_bg"], "fg": t["deshabilitado_fg"]}

        if self._variant == "primary":
            mapa = {
                "normal": (t["accent"], "#ffffff"),
                "hover": (t["accent_hover"], "#ffffff"),
                "active": (t["accent_active"], "#ffffff"),
            }
        elif self._variant == "danger":
            mapa = {
                "normal": (t["surface"], t["error"]),
                "hover": (t["secundario_hover"], t["error"]),
                "active": (t["secundario_active"], t["error"]),
            }
        else:
            mapa = {
                "normal": (t["secundario"], t["texto"]),
                "hover": (t["secundario_hover"], t["texto"]),
                "active": (t["secundario_active"], t["texto"]),
            }

        bg, fg = mapa[estado]
        return {"bg": bg, "fg": fg}

    def _aplicar_estado(self, estado):
        if self._deshabilitado:
            return
        c = self._paleta(estado)
        self._inner.configure(bg=c["bg"], fg=c["fg"])

    def _on_enter(self, _event):
        if not self._presionado:
            self._aplicar_estado("hover")

    def _on_leave(self, _event):
        self._presionado = False
        self._aplicar_estado("normal")

    def _on_press(self, _event):
        self._presionado = True
        self._aplicar_estado("active")

    def _on_release(self, _event):
        self._presionado = False
        self._aplicar_estado("hover")
        if self._command and not self._deshabilitado:
            self._command()

    def config_texto(self, texto):
        self._inner.configure(text=texto)

    def config_estado(self, estado):
        deshabilitado = estado == "disabled"
        if deshabilitado == self._deshabilitado:
            return
        self._deshabilitado = deshabilitado

        if deshabilitado:
            for seq in ("<Enter>", "<Leave>", "<ButtonPress-1>", "<ButtonRelease-1>"):
                self._inner.unbind(seq)
                self.unbind(seq)
            self._inner.configure(cursor="arrow", **self._paleta("normal"))
        else:
            for w in (self, self._inner):
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)
                w.bind("<ButtonPress-1>", self._on_press)
                w.bind("<ButtonRelease-1>", self._on_release)
            self._inner.configure(cursor="hand2")
            self._aplicar_estado("normal")


class DetectorCarrosFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Carros")
        self.root.geometry("1000x740")
        self.root.minsize(900, 660)
        self.modo_oscuro = False
        self.tema = TEMA_CLARO.copy()
        self.root.configure(bg=self.tema["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        self._fotos = []
        self._configurar_icono_ventana()

        self.ruta_imagen = None
        self.array_imagen = None
        self.camera_activa = False
        self.preview_vivo = True
        self.cap = None
        self.preview_job = None
        self.photo_preview = None
        self.umbral = 0.5
        self._dnd_activo = False
        self._resaltando_drop = False

        self.cargar_umbral()
        self.cargar_modelo()
        self.crear_interfaz()
        self._configurar_ttk()
        self._configurar_drag_drop()
        self._actualizar_zona_drop()

    def _guardar_foto(self, foto):
        self._fotos.append(foto)
        return foto

    def _configurar_icono_ventana(self):
        if not os.path.exists(ICONO_VENTANA):
            return
        try:
            img = Image.open(ICONO_VENTANA)
            img_icon = img.resize((32, 32), Image.Resampling.LANCZOS)
            foto = ImageTk.PhotoImage(img_icon)
            self.root.iconphoto(True, self._guardar_foto(foto))
            if sys.platform == "win32":
                ico_path = os.path.join(BASE_DIR, "_icono_temp.ico")
                img_icon.save(ico_path, format="ICO")
                try:
                    self.root.iconbitmap(ico_path)
                except tk.TclError:
                    pass
        except OSError as e:
            print(f"No se pudo cargar icono de ventana: {e}")

    def _configurar_ttk(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Minimal.Horizontal.TProgressbar",
            troughcolor=self.tema["borde"],
            background=self.tema["accent"],
            bordercolor=self.tema["borde"],
            lightcolor=self.tema["accent"],
            darkcolor=self.tema["accent"],
            thickness=8,
        )

    def cargar_umbral(self):
        ruta = os.path.join(BASE_DIR, "umbral_optimo.json")
        if os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as f:
                    self.umbral = float(json.load(f).get("umbral", 0.5))
                print(f"Umbral de deteccion: {self.umbral:.2f}")
            except (json.JSONDecodeError, TypeError, ValueError):
                self.umbral = 0.5

    def cargar_modelo(self):
        try:
            if os.path.exists("modelo_carros.h5"):
                self.modelo = tf.keras.models.load_model("modelo_carros.h5", compile=False)
                self.modelo_cargado = True
                print("Modelo cargado correctamente")
            else:
                self.modelo_cargado = False
                print("No se encuentra modelo_carros.h5")
        except Exception as e:
            self.modelo_cargado = False
            print(f"Error: {e}")

    def crear_interfaz(self):
        t = self.tema

        self.header = tk.Frame(self.root, bg=t["surface"], height=72)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        self._linea_header = tk.Frame(self.header, bg=t["borde"], height=1)
        self._linea_header.pack(side="bottom", fill="x")

        header_inner = tk.Frame(self.header, bg=t["surface"])
        header_inner.pack(side="left", padx=24, pady=12)

        self._lbl_icono_titulo = tk.Label(header_inner, bg=t["surface"])
        self._lbl_icono_titulo.pack(side="left", padx=(0, 12))
        icono = _cargar_icono(ICONO_TITULO, (44, 44))
        if icono:
            self._lbl_icono_titulo.configure(image=self._guardar_foto(icono))

        self._lbl_titulo = tk.Label(
            header_inner,
            text="Detector de Carros",
            font=FONT_TITLE,
            fg=t["texto"],
            bg=t["surface"],
        )
        self._lbl_titulo.pack(side="left")

        self.label_estado = tk.Label(self.header, text="", font=FONT_SMALL, bg=t["surface"])
        self.label_estado.pack(side="right", padx=24)
        if self.modelo_cargado:
            self.label_estado.config(text="Modelo listo", fg=t["exito"])
        else:
            self.label_estado.config(text="Modelo no encontrado", fg=t["error"])

        self.main = tk.Frame(self.root, bg=t["bg"])
        self.main.pack(fill="both", expand=True, padx=20, pady=16)

        self.sidebar = tk.Frame(self.main, bg=t["bg"], width=200)
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))
        self.sidebar.pack_propagate(False)

        self.btn_camara = BotonMinimal(
            self.sidebar,
            "Activar camara",
            command=self.toggle_camara,
            variant="camera",
            tema=t,
        )
        self.btn_camara.pack(fill="x", pady=(0, 8))

        self.btn_imagen = BotonMinimal(
            self.sidebar,
            "Seleccionar imagen",
            command=self.accion_imagen,
            variant="secondary",
            tema=t,
        )
        self.btn_imagen.pack(fill="x", pady=8)

        self.btn_detectar = BotonMinimal(
            self.sidebar,
            "Detectar",
            command=self.detectar,
            variant="primary",
            deshabilitado=True,
            tema=t,
        )
        self.btn_detectar.pack(fill="x", pady=8)

        self.btn_limpiar = BotonMinimal(
            self.sidebar, "Limpiar", command=self.limpiar, variant="danger", tema=t
        )
        self.btn_limpiar.pack(fill="x", pady=8)

        self.content = tk.Frame(self.main, bg=t["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self.card_imagen = tk.Frame(
            self.content, bg=t["surface"], highlightbackground=t["borde"], highlightthickness=1
        )
        self.card_imagen.pack(fill="both", expand=True, pady=(0, 12))

        self.frame_imagen = tk.Frame(self.card_imagen, bg=t["surface"], height=400)
        self.frame_imagen.pack(fill="both", expand=True, padx=1, pady=1)
        self.frame_imagen.pack_propagate(False)

        self.label_imagen = tk.Label(
            self.frame_imagen,
            text="No hay imagen seleccionada",
            font=FONT_SUBTITLE,
            bg=t["surface"],
            fg=t["texto_suave"],
        )
        self.label_imagen.pack(expand=True, fill="both")

        self.card_result = tk.Frame(
            self.content, bg=t["surface"], highlightbackground=t["borde"], highlightthickness=1
        )
        self.card_result.pack(fill="x")

        self.frame_resultado = tk.Frame(self.card_result, bg=t["surface"], padx=20, pady=16)
        self.frame_resultado.pack(fill="x")

        self.label_resultado = tk.Label(
            self.frame_resultado,
            text="Resultado: —",
            font=FONT_RESULT,
            bg=t["surface"],
            fg=t["texto"],
        )
        self.label_resultado.pack(anchor="w")

        self.label_probabilidad = tk.Label(
            self.frame_resultado,
            text="Probabilidad: —",
            font=FONT_BODY,
            bg=t["surface"],
            fg=t["texto_suave"],
        )
        self.label_probabilidad.pack(anchor="w", pady=(6, 0))

        self.label_transformacion = tk.Label(
            self.frame_resultado,
            text="",
            font=FONT_SMALL,
            bg=t["surface"],
            fg=t["texto_suave"],
            wraplength=640,
            justify="left",
        )
        self.label_transformacion.pack(anchor="w", pady=(8, 0))

        self.progress = ttk.Progressbar(
            self.frame_resultado,
            length=400,
            mode="determinate",
            style="Minimal.Horizontal.TProgressbar",
        )
        self.progress.pack(anchor="w", pady=(12, 0), fill="x")

        self.footer = tk.Frame(self.root, bg=t["bg"], height=44)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self.btn_luna = tk.Label(
            self.footer,
            text="☽",
            font=FONT_LUNA,
            fg=t["luna_fg"],
            bg=t["bg"],
            cursor="hand2",
            padx=16,
            pady=6,
        )
        self.btn_luna.pack(side="left", padx=12, pady=4)
        self.btn_luna.bind(
            "<Enter>",
            lambda e, tema=t: self.btn_luna.configure(fg=tema["luna_hover"]),
        )
        self.btn_luna.bind(
            "<Leave>",
            lambda e: self.btn_luna.configure(fg=self.tema["luna_fg"]),
        )
        self.btn_luna.bind("<Button-1>", lambda e: self.toggle_modo_oscuro())

    def _zona_limpia(self):
        """Sin camara activa y sin imagen cargada."""
        return not self.camera_activa and self.array_imagen is None

    def _configurar_drag_drop(self):
        """Registra arrastrar y soltar en la zona de imagen."""
        try:
            from tkinterdnd2 import DND_FILES

            self._dnd_activo = True
            for widget in (self.card_imagen, self.frame_imagen, self.label_imagen):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop_archivos)
                widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            return
        except Exception as e:
            print(f"tkinterdnd2 no disponible: {e}")

        if sys.platform == "win32":
            try:
                import windnd

                self._dnd_activo = True
                windnd.hook_dropfiles(self.frame_imagen, func=self._on_drop_windnd)
                windnd.hook_dropfiles(self.label_imagen, func=self._on_drop_windnd)
                return
            except ImportError:
                print("Instala tkinterdnd2 o windnd para arrastrar imagenes.")

    def _on_drop_windnd(self, rutas):
        if not self._zona_limpia():
            return
        for ruta in rutas:
            ruta = ruta.strip().strip('"')
            if _es_archivo_imagen(ruta):
                self._cargar_archivo_imagen(ruta)
                break

    def _on_drop_archivos(self, event):
        if not self._zona_limpia():
            return
        self._restaurar_borde_drop()
        for ruta in _parsear_rutas_drop(event.data):
            if _es_archivo_imagen(ruta):
                self._cargar_archivo_imagen(ruta)
                break

    def _on_drag_enter(self, _event):
        if not self._zona_limpia():
            return
        self._resaltando_drop = True
        self.card_imagen.configure(
            highlightbackground=self.tema["accent"],
            highlightthickness=2,
        )

    def _on_drag_leave(self, _event):
        self._restaurar_borde_drop()

    def _restaurar_borde_drop(self):
        if not self._resaltando_drop:
            return
        self._resaltando_drop = False
        self.card_imagen.configure(
            highlightbackground=self.tema["borde"],
            highlightthickness=1,
        )

    def _actualizar_zona_drop(self):
        """Actualiza texto y estilo segun si se puede arrastrar una imagen."""
        self._restaurar_borde_drop()
        if self._zona_limpia():
            self.label_imagen.config(
                text=f"{TEXTO_ARRASTRAR}\n{TEXTO_ARRASTRAR_SUB}",
                image="",
                fg=self.tema["accent"] if self._dnd_activo else self.tema["texto_suave"],
            )
        elif self.camera_activa and self.preview_vivo:
            self.label_imagen.config(text="", image="", fg=self.tema["texto_suave"])
        elif self.array_imagen is None:
            self.label_imagen.config(
                image="",
                text=TEXTO_SIN_IMAGEN,
                fg=self.tema["texto_suave"],
            )

    def _cargar_archivo_imagen(self, archivo):
        self.preview_vivo = not self.camera_activa
        try:
            resultado = procesar_imagen_seleccionada(archivo)
        except Exception as e:
            messagebox.showerror(
                "Error al procesar imagen",
                f"No se pudo cargar la imagen.\n\nDetalle: {e}",
            )
            return
        self.aplicar_resultado(resultado)

    def toggle_modo_oscuro(self):
        self.modo_oscuro = not self.modo_oscuro
        self.tema = TEMA_OSCURO.copy() if self.modo_oscuro else TEMA_CLARO.copy()
        self._aplicar_tema()

    def _aplicar_tema(self):
        t = self.tema
        self.root.configure(bg=t["bg"])
        self.header.configure(bg=t["surface"])
        self._linea_header.configure(bg=t["borde"])
        self._lbl_icono_titulo.configure(bg=t["surface"])
        self._lbl_titulo.configure(bg=t["surface"], fg=t["texto"])
        self.label_estado.configure(bg=t["surface"])
        if self.modelo_cargado:
            self.label_estado.configure(fg=t["exito"])
        else:
            self.label_estado.configure(fg=t["error"])

        self.main.configure(bg=t["bg"])
        self.sidebar.configure(bg=t["bg"])
        self.content.configure(bg=t["bg"])
        self.footer.configure(bg=t["bg"])
        self.btn_luna.configure(bg=t["bg"], fg=t["luna_fg"])

        for btn in (
            self.btn_camara,
            self.btn_imagen,
            self.btn_detectar,
            self.btn_limpiar,
        ):
            btn.set_tema(t)

        self.card_imagen.configure(
            bg=t["surface"], highlightbackground=t["borde"]
        )
        self.frame_imagen.configure(bg=t["surface"])
        self.label_imagen.configure(bg=t["surface"], fg=t["texto_suave"])
        self.card_result.configure(bg=t["surface"], highlightbackground=t["borde"])
        self.frame_resultado.configure(bg=t["surface"])
        self.label_resultado.configure(bg=t["surface"])
        self.label_probabilidad.configure(bg=t["surface"], fg=t["texto_suave"])
        self.label_transformacion.configure(bg=t["surface"], fg=t["texto_suave"])

        if self.label_resultado.cget("text") == "Es un carro":
            self.label_resultado.configure(fg=t["exito"])
        elif self.label_resultado.cget("text") == "No es un carro":
            self.label_resultado.configure(fg=t["error"])
        else:
            self.label_resultado.configure(fg=t["texto"])

        self._configurar_ttk()
        self._actualizar_zona_drop()

    def _actualizar_seleccion_botones(self):
        self.btn_camara.set_seleccionado(self.camera_activa)

    def accion_imagen(self):
        if self.camera_activa:
            self.tomar_captura()
        else:
            self.seleccionar_imagen()

    def toggle_camara(self):
        if self.camera_activa:
            self.desactivar_camara()
        else:
            self.activar_camara()

    def activar_camara(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror(
                "Camara",
                "No se pudo abrir la camara.\nVerifica que este conectada y disponible.",
            )
            self.cap = None
            return

        self.camera_activa = True
        self.preview_vivo = self.array_imagen is None
        self.btn_camara.config_texto("Desactivar camara")
        self.btn_imagen.config_texto("Tomar captura")
        self._actualizar_seleccion_botones()

        if self.preview_vivo:
            self.label_imagen.config(text="", image="")
            self.actualizar_vista_camara()
        else:
            self.mostrar_imagen_guardada()
        self._actualizar_zona_drop()

    def desactivar_camara(self):
        self.camera_activa = False
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
            self.preview_job = None
        if self.cap:
            self.cap.release()
            self.cap = None

        self.btn_camara.config_texto("Activar camara")
        self.btn_imagen.config_texto("Seleccionar imagen")
        self._actualizar_seleccion_botones()

        if self.array_imagen is None:
            self.preview_vivo = True
        else:
            self.mostrar_imagen_guardada()
        self._actualizar_zona_drop()

    def mostrar_imagen_guardada(self):
        if self.array_imagen is None:
            return
        arr = (self.array_imagen * 255).astype(np.uint8)
        self.mostrar_imagen(Image.fromarray(arr))

    def actualizar_vista_camara(self):
        if not self.camera_activa or self.cap is None:
            return

        if not self.preview_vivo:
            self.preview_job = self.root.after(100, self.actualizar_vista_camara)
            return

        ok, frame = self.cap.read()
        if ok:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            vista = img.copy()
            vista.thumbnail((700, 380), Image.Resampling.LANCZOS)
            self.photo_preview = ImageTk.PhotoImage(vista)
            self.label_imagen.config(image=self.photo_preview, text="")
            self.label_imagen.image = self.photo_preview

        self.preview_job = self.root.after(30, self.actualizar_vista_camara)

    def tomar_captura(self):
        if not self.camera_activa or self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("Error", "No se pudo capturar el frame de la camara.")
            return

        os.makedirs(CARPETA_CAPTURAS, exist_ok=True)
        ruta_captura = os.path.join(CARPETA_CAPTURAS, f"captura_{int(time.time())}.jpg")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img.save(ruta_captura, format="JPEG", quality=95)

        try:
            resultado = procesar_imagen_pil(img, ruta_salida=ruta_captura)
        except Exception as e:
            messagebox.showerror(
                "Error al procesar captura",
                f"No se pudo procesar la imagen.\n\nDetalle: {e}",
            )
            return

        self.preview_vivo = False
        self.aplicar_resultado(resultado)

    def aplicar_resultado(self, resultado):
        self.ruta_imagen = resultado["ruta_jpg"]
        self.array_imagen = resultado["array_modelo"]
        self.mostrar_imagen(resultado["imagen_pil"])
        self.btn_detectar.config_estado("normal")

        if resultado["fue_transformada"]:
            self.label_transformacion.config(
                text="Imagen redimensionada a 224×224 RGB para la deteccion."
            )
        else:
            self.label_transformacion.config(
                text="Imagen 224×224 RGB lista (sin transformaciones)."
            )

        self.label_resultado.config(text="Resultado: —", fg=self.tema["texto"])
        self.label_probabilidad.config(text="Probabilidad: —")
        self.progress["value"] = 0
        self._actualizar_zona_drop()

    def seleccionar_imagen(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imagenes", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if archivo:
            self._cargar_archivo_imagen(archivo)

    def mostrar_imagen(self, img):
        vista = img.copy()
        vista.thumbnail((700, 380), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(vista)
        self.label_imagen.config(image=self.photo, text="")
        self.label_imagen.image = self.photo

    def detectar(self):
        if not self.modelo_cargado:
            messagebox.showerror("Error", "Modelo no cargado")
            return

        if not self.ruta_imagen:
            messagebox.showerror("Error", "Selecciona o captura una imagen primero")
            return

        if self.array_imagen is None:
            messagebox.showerror("Error", "Selecciona y procesa una imagen primero")
            return

        try:
            img_array = np.expand_dims(self.array_imagen, axis=0)
            valor_crudo = float(self.modelo.predict(img_array, verbose=0)[0][0])
            es_carro = valor_crudo >= self.umbral

            if es_carro:
                self.label_resultado.config(text="Es un carro", fg=self.tema["exito"])
                probabilidad = valor_crudo
            else:
                self.label_resultado.config(text="No es un carro", fg=self.tema["error"])
                probabilidad = 1 - valor_crudo

            confianza = probabilidad * 100
            self.label_probabilidad.config(
                text=(
                    f"Confianza: {probabilidad:.2%} ({confianza:.1f}%) "
                    f"· Umbral {self.umbral:.2f}"
                )
            )
            self.progress["value"] = confianza
            print(f"Valor crudo: {valor_crudo:.4f} -> {'CARRO' if es_carro else 'NO CARRO'}")

        except Exception as e:
            messagebox.showerror("Error", f"Error al detectar: {e}")

    def limpiar(self):
        self.ruta_imagen = None
        self.array_imagen = None
        self.preview_vivo = True
        self.label_transformacion.config(text="")
        self.label_resultado.config(text="Resultado: —", fg=self.tema["texto"])
        self.label_probabilidad.config(text="Probabilidad: —")
        self.progress["value"] = 0
        self.btn_detectar.config_estado("disabled")

        if self.camera_activa:
            self.label_imagen.config(text="", image="")
            self.actualizar_vista_camara()
        self._actualizar_zona_drop()

    def al_cerrar(self):
        self.desactivar_camara()
        self.root.destroy()


if __name__ == "__main__":
    root = crear_ventana_raiz()
    app = DetectorCarrosFinal(root)
    root.mainloop()
