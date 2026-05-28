# ==============================================
# TRANSFORMACIONES DE IMAGEN - ESPECIFICACIONES DEL PROYECTO
# ==============================================

import os
import random
import numpy as np
from PIL import Image, ImageEnhance

TAMANO_IMAGEN = (224, 224)
CANALES = 3
CARPETA_SALIDA = "imagenes_transformadas"


def _nombre_salida(ruta_entrada):
    base = os.path.splitext(os.path.basename(ruta_entrada))[0]
    return os.path.join(CARPETA_SALIDA, f"{base}_224.jpg")


def cumple_especificaciones(img):
    """
    True si la imagen ya cumple resolucion 224x224 y 3 canales RGB.
    En ese caso no se aplican transformaciones de aumento.
    """
    return img.size == TAMANO_IMAGEN and img.mode == "RGB"


def normalizar_base(img):
    """Convierte a RGB y redimensiona exactamente a 224x224."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    if img.size != TAMANO_IMAGEN:
        img = img.resize(TAMANO_IMAGEN, Image.Resampling.LANCZOS)
    return img


def _recortar_centro(img, ancho, alto):
    w, h = img.size
    izq = max(0, (w - ancho) // 2)
    sup = max(0, (h - alto) // 2)
    return img.crop((izq, sup, izq + ancho, sup + alto))


def _aplicar_zoom(img, zoom_range=0.2):
    """Zoom aleatorio entre (1 - zoom_range) y (1 + zoom_range)."""
    w, h = img.size
    factor = random.uniform(1.0 - zoom_range, 1.0 + zoom_range)
    nw = max(1, int(w * factor))
    nh = max(1, int(h * factor))
    redim = img.resize((nw, nh), Image.Resampling.LANCZOS)
    if factor >= 1.0:
        return _recortar_centro(redim, w, h)
    lienzo = Image.new("RGB", (w, h), (0, 0, 0))
    lienzo.paste(redim, ((w - nw) // 2, (h - nh) // 2))
    return lienzo


def _aplicar_desplazamiento(img, fraccion=0.1):
    """Desplazamiento lateral/vertical hasta fraccion del tamano."""
    w, h = img.size
    dx = int(random.uniform(-fraccion, fraccion) * w)
    dy = int(random.uniform(-fraccion, fraccion) * h)
    lienzo = Image.new("RGB", (w, h), (0, 0, 0))
    lienzo.paste(img, (dx, dy))
    return lienzo


def aplicar_transformaciones(img_rgb_224):
    """
    Aplica aumento de datos (solo cuando la imagen no cumple especificaciones).
    Entrada/salida: imagen PIL RGB 224x224.
    """
    img = img_rgb_224.copy()

    angulo = random.uniform(-20, 20)
    img = img.rotate(
        angulo,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0),
        expand=False,
    )

    if random.random() < 0.5:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    brillo = random.uniform(0.8, 1.2)
    img = ImageEnhance.Brightness(img).enhance(brillo)

    img = _aplicar_zoom(img, zoom_range=0.2)
    img = _aplicar_desplazamiento(img, fraccion=0.1)

    if img.size != TAMANO_IMAGEN:
        img = img.resize(TAMANO_IMAGEN, Image.Resampling.LANCZOS)

    return img


def guardar_jpg(img, ruta_salida):
    """Guarda la imagen en formato JPG con 3 canales RGB."""
    carpeta = os.path.dirname(os.path.abspath(ruta_salida))
    os.makedirs(carpeta, exist_ok=True)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(ruta_salida, format="JPEG", quality=95)


def imagen_a_array_modelo(img):
    """Convierte PIL RGB 224x224 a array normalizado para el modelo."""
    arr = np.array(img, dtype=np.float32)
    if arr.shape != (224, 224, 3):
        raise ValueError(f"Dimensiones invalidas: {arr.shape}")
    return arr / 255.0


def _procesar_desde_pil(img, ruta_entrada=None, ruta_salida=None):
    """Logica comun para archivo o imagen PIL en memoria."""
    ya_cumple = cumple_especificaciones(img)

    if ya_cumple:
        img_modelo = img.copy()
        if ruta_entrada and os.path.exists(ruta_entrada):
            ruta_uso = os.path.abspath(ruta_entrada)
        else:
            os.makedirs(CARPETA_SALIDA, exist_ok=True)
            base = "captura" if ruta_salida is None else os.path.splitext(
                os.path.basename(ruta_salida)
            )[0]
            ruta_uso = ruta_salida or os.path.join(CARPETA_SALIDA, f"{base}_224.jpg")
            guardar_jpg(img_modelo, ruta_uso)
    else:
        img_modelo = normalizar_base(img)
        img_augmentada = aplicar_transformaciones(img_modelo.copy())
        ruta_uso = ruta_salida or (
            _nombre_salida(ruta_entrada) if ruta_entrada else os.path.join(
                CARPETA_SALIDA, "captura_224.jpg"
            )
        )
        guardar_jpg(img_augmentada, ruta_uso)

    return {
        "ruta_jpg": ruta_uso,
        "imagen_pil": img_modelo,
        "array_modelo": imagen_a_array_modelo(img_modelo),
        "fue_transformada": not ya_cumple,
    }


def procesar_imagen_lote(ruta_entrada):
    """
    Preprocesado ligero para inferencia por lote (sin escritura en disco).
    """
    if not os.path.exists(ruta_entrada):
        raise FileNotFoundError(f"No se encuentra el archivo: {ruta_entrada}")

    with Image.open(ruta_entrada) as img:
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_modelo = normalizar_base(img)
        return {
            "ruta": os.path.abspath(ruta_entrada),
            "nombre": os.path.basename(ruta_entrada),
            "array_modelo": imagen_a_array_modelo(img_modelo),
        }


def procesar_imagen_seleccionada(ruta_entrada, ruta_salida=None):
    """
    Prepara la imagen para el modelo desde un archivo en disco.
    """
    if not os.path.exists(ruta_entrada):
        raise FileNotFoundError(f"No se encuentra el archivo: {ruta_entrada}")

    with Image.open(ruta_entrada) as img:
        img.load()
        return _procesar_desde_pil(img, ruta_entrada=ruta_entrada, ruta_salida=ruta_salida)


def procesar_imagen_pil(img, ruta_salida=None):
    """Prepara una imagen PIL para el modelo (p. ej. captura de camara)."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    return _procesar_desde_pil(img.copy(), ruta_salida=ruta_salida)
