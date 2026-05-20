# ==============================================
# DETECTOR DE CARROS - PROYECTO UNIVERSITARIO
# VERSION LIMPIA - SIN TEXTO DE ESPECIFICACIONES
# ==============================================

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
import tensorflow as tf
import os

class DetectorCarrosFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Carros - Proyecto Universitario")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0f0f0')
        
        self.ruta_imagen = None
        
        # Especificaciones del modelo
        self.TAMANO_REQUERIDO = (224, 224)
        self.CANALES_REQUERIDOS = 3
        
        # Cargar modelo
        self.cargar_modelo()
        
        # Crear interfaz
        self.crear_interfaz()
    
    def cargar_modelo(self):
        """Cargar el modelo entrenado"""
        try:
            if os.path.exists("modelo_carros.h5"):
                self.modelo = tf.keras.models.load_model("modelo_carros.h5")
                self.modelo_cargado = True
                print("Modelo cargado correctamente")
            else:
                self.modelo_cargado = False
                print("No se encuentra modelo_carros.h5")
        except Exception as e:
            self.modelo_cargado = False
            print(f"Error: {e}")
    
    def validar_y_preprocesar(self, ruta):
        """
        Valida la imagen segun las especificaciones del modelo.
        Retorna (imagen_procesada, mensaje_error)
        """
        try:
            # 1. Verificar que el archivo existe
            if not os.path.exists(ruta):
                return None, "ERROR: El archivo no existe"
            
            # 2. Verificar extension
            extensiones_validas = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
            if not ruta.lower().endswith(extensiones_validas):
                return None, f"ERROR: Formato no soportado.\nFormatos aceptados: JPG, JPEG, PNG, BMP, GIF"
            
            # 3. Abrir imagen
            try:
                img_original = Image.open(ruta)
            except Exception as e:
                return None, f"ERROR: La imagen esta corrupta o no es valida"
            
            # 4. Obtener dimensiones ORIGINALES
            ancho_original, alto_original = img_original.size
            
            # 5. VERIFICAR TAMANO ORIGINAL
            if ancho_original != self.TAMANO_REQUERIDO[0] or alto_original != self.TAMANO_REQUERIDO[1]:
                return None, f"ERROR: Tamano de imagen incorrecto\n\nDimensiones requeridas: {self.TAMANO_REQUERIDO[0]}x{self.TAMANO_REQUERIDO[1]} pixeles\nDimensiones de su imagen: {ancho_original}x{alto_original} pixeles"
            
            # 6. Verificar canales de color
            modo = img_original.mode
            if modo == 'RGB':
                canales = 3
            elif modo == 'RGBA':
                canales = 4
                return None, f"ERROR: La imagen tiene canal alfa (RGBA)\n\nEl modelo requiere imagenes RGB (3 canales)"
            elif modo == 'L':
                canales = 1
                return None, f"ERROR: La imagen es blanco y negro\n\nEl modelo requiere imagenes a COLOR (RGB)"
            else:
                canales = len(img_original.getbands())
                if canales != 3:
                    return None, f"ERROR: Numero de canales incorrecto\n\nCanales requeridos: 3 (RGB)"
            
            # 7. Verificar que la imagen no este corrupta
            if ancho_original < 10 or alto_original < 10:
                return None, f"ERROR: Imagen demasiado pequena"
            
            # 8. Convertir a array y normalizar
            img_array = np.array(img_original, dtype=np.float32)
            img_array = img_array / 255.0
            
            # 9. Verificar dimensiones finales del array
            if img_array.shape != (224, 224, 3):
                return None, f"ERROR: Dimensiones del array incorrectas"
            
            # Exito
            return img_array, None
            
        except Exception as e:
            return None, f"ERROR inesperado: {str(e)}"
    
    def crear_interfaz(self):
        # Titulo con fondo azul
        titulo_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        titulo_frame.pack(fill='x')
        
        titulo = tk.Label(titulo_frame, text="DETECTOR DE CARROS", 
                          font=("Arial", 24, "bold"), 
                          fg="white", bg='#2c3e50')
        titulo.pack(pady=20)
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Frame para la imagen
        self.frame_imagen = tk.Frame(main_frame, bd=2, relief="solid", 
                                      bg='white', height=400, width=600)
        self.frame_imagen.pack(pady=10, fill='both', expand=True)
        self.frame_imagen.pack_propagate(False)
        
        self.label_imagen = tk.Label(self.frame_imagen, text="No hay imagen seleccionada",
                                      font=("Arial", 14), bg='white', fg='gray')
        self.label_imagen.pack(expand=True, fill='both')
        
        # Frame para botones
        frame_botones = tk.Frame(main_frame, bg='#f0f0f0')
        frame_botones.pack(pady=15)
        
        # Boton seleccionar imagen
        btn_seleccionar = tk.Button(frame_botones, 
                                    text="SELECCIONAR IMAGEN",
                                    command=self.seleccionar_imagen,
                                    font=("Arial", 12, "bold"),
                                    bg='#3498db', fg='white',
                                    padx=20, pady=10,
                                    cursor='hand2')
        btn_seleccionar.pack(side='left', padx=10)
        
        # Boton detectar
        self.btn_detectar = tk.Button(frame_botones,
                                      text="DETECTAR CARRO",
                                      command=self.detectar,
                                      font=("Arial", 12, "bold"),
                                      bg='#27ae60', fg='white',
                                      padx=20, pady=10,
                                      cursor='hand2',
                                      state='disabled')
        self.btn_detectar.pack(side='left', padx=10)
        
        # Boton limpiar
        btn_limpiar = tk.Button(frame_botones,
                                text="LIMPIAR",
                                command=self.limpiar,
                                font=("Arial", 12, "bold"),
                                bg='#e74c3c', fg='white',
                                padx=20, pady=10,
                                cursor='hand2')
        btn_limpiar.pack(side='left', padx=10)
        
        # Frame para resultados
        frame_resultado = tk.Frame(main_frame, bd=2, relief="solid", 
                                    bg='white', padx=15, pady=15)
        frame_resultado.pack(pady=10, fill='x')
        
        # Etiqueta de resultado principal
        self.label_resultado = tk.Label(frame_resultado, text="Resultado: ---",
                                        font=("Arial", 18, "bold"),
                                        bg='white')
        self.label_resultado.pack(pady=5)
        
        # Etiqueta de probabilidad
        self.label_probabilidad = tk.Label(frame_resultado, 
                                           text="Probabilidad: ---",
                                           font=("Arial", 12),
                                           bg='white')
        self.label_probabilidad.pack()
        
        # Barra de progreso
        self.progress = ttk.Progressbar(frame_resultado, length=500, 
                                        mode='determinate')
        self.progress.pack(pady=10)
        
        # Estado del modelo
        if self.modelo_cargado:
            estado_texto = "Modelo cargado correctamente"
            estado_color = "green"
        else:
            estado_texto = "Modelo no encontrado"
            estado_color = "red"
        
        estado_label = tk.Label(self.root, text=estado_texto,
                                font=("Arial", 10),
                                fg=estado_color, bg='#f0f0f0')
        estado_label.pack(side='bottom', pady=10)
    
    def seleccionar_imagen(self):
        """Abrir dialogo para seleccionar imagen"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imagenes", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if archivo:
            self.ruta_imagen = archivo
            self.mostrar_imagen(archivo)
            self.btn_detectar.config(state='normal')
            # Limpiar resultado anterior
            self.label_resultado.config(text="Resultado: ---", fg="black")
            self.label_probabilidad.config(text="Probabilidad: ---")
            self.progress['value'] = 0
    
    def mostrar_imagen(self, ruta):
        """Mostrar imagen en la interfaz"""
        img = Image.open(ruta)
        max_size = (550, 350)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.label_imagen.config(image=self.photo, text="")
        self.label_imagen.image = self.photo
        
    def detectar(self):
        """Ejecutar deteccion con validacion automatica"""
        if not self.modelo_cargado:
            messagebox.showerror("Error", "Modelo no cargado")
            return
        
        if not self.ruta_imagen:
            messagebox.showerror("Error", "Selecciona una imagen primero")
            return
        
        # Validar y preprocesar la imagen
        img_array, mensaje = self.validar_y_preprocesar(self.ruta_imagen)
        
        # Si hay error, mostrarlo y detener
        if img_array is None:
            messagebox.showerror("ERROR DE VALIDACION", mensaje)
            return
        
        # Si llegamos aqui, la imagen es valida
        try:
            # Anadir dimension de batch
            img_array = np.expand_dims(img_array, axis=0)
            
            # Predecir
            valor_crudo = self.modelo.predict(img_array, verbose=0)[0][0]

            # INTERPRETACION NORMAL
            # Valores altos (>0.5) = CARRO, valores bajos (<0.5) = NO CARRO
            es_carro = valor_crudo > 0.5

            if es_carro:
                self.label_resultado.config(text="ES UN CARRO", 
                                        fg="#27ae60")
                self.progress['style'] = 'green.Horizontal.TProgressbar'
                probabilidad = valor_crudo
            else:
                self.label_resultado.config(text="NO ES UN CARRO", 
                                        fg="#e74c3c")
                self.progress['style'] = 'red.Horizontal.TProgressbar'
                probabilidad = 1 - valor_crudo

            confianza = probabilidad * 100
            
            self.label_probabilidad.config(text=f"Probabilidad de ser carro: {probabilidad:.4f} ({confianza:.2f}%)")
            self.progress['value'] = confianza
            
            # Para depuracion (opcional)
            print(f"Valor crudo: {valor_crudo:.4f} -> {'CARRO' if es_carro else 'NO CARRO'}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al detectar: {e}")
    
    def limpiar(self):
        """Limpiar todo"""
        self.ruta_imagen = None
        self.label_imagen.config(image='', text="No hay imagen seleccionada")
        self.label_resultado.config(text="Resultado: ---", fg="black")
        self.label_probabilidad.config(text="Probabilidad: ---")
        self.progress['value'] = 0
        self.btn_detectar.config(state='disabled')

# Ejecutar la aplicacion
if __name__ == "__main__":
    root = tk.Tk()
    app = DetectorCarrosFinal(root)
    root.mainloop()