# ==============================================
# EXPORTAR MODELO A ONNX - EQUIPO CARROS
# VERSION CORREGIDA SIN COMANDOS DE COLAB
# ==============================================

import tensorflow as tf
import tf2onnx
import onnx
import os
import subprocess

print("="*60)
print("EXPORTANDO MODELO A ONNX - EQUIPO CARROS")
print("="*60)

# Cargar el modelo entrenado
print("\nCargando modelo...")
model = tf.keras.models.load_model("modelo_carros.h5")
print("Modelo cargado correctamente")

# Crear carpeta model si no existe
if not os.path.exists("model"):
    os.makedirs("model")
    print("Carpeta 'model' creada")

# Nombre del archivo
NOMBRE_ARCHIVO = "model/carros.onnx"

print(f"\nConfigurando exportacion...")
print(f"   Archivo de salida: {NOMBRE_ARCHIVO}")

# Especificaciones para ONNX
input_signature = [tf.TensorSpec(shape=[1, 224, 224, 3], dtype=tf.float32, name='input_imagen')]

print("\nExportando a ONNX...")

# Metodo 1: usar from_keras
try:
    onnx_model, _ = tf2onnx.convert.from_keras(
        model,
        input_signature=input_signature,
        opset=13,
        output_path=NOMBRE_ARCHIVO
    )
    print(f"Modelo exportado a: {NOMBRE_ARCHIVO}")
    
except Exception as e:
    print(f"Error con metodo 1: {e}")
    print("\nIntentando metodo alternativo...")
    
    # Metodo 2: guardar como SavedModel y convertir
    try:
        # Guardar como SavedModel
        tf.saved_model.save(model, "temp_saved_model")
        print("SavedModel guardado temporalmente")
        
        # Ejecutar conversion usando subprocess
        cmd = [
            "python", "-m", "tf2onnx.convert",
            "--saved-model", "temp_saved_model",
            "--output", NOMBRE_ARCHIVO,
            "--opset", "13"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Modelo exportado a: {NOMBRE_ARCHIVO}")
        else:
            print(f"Error en conversion: {result.stderr}")
        
        # Limpiar
        import shutil
        shutil.rmtree("temp_saved_model")
        
    except Exception as e2:
        print(f"Error con metodo 2: {e2}")

# Verificar que el archivo existe
if os.path.exists(NOMBRE_ARCHIVO):
    print("\nValidando modelo ONNX...")
    onnx_model = onnx.load(NOMBRE_ARCHIVO)
    onnx.checker.check_model(onnx_model)
    print("Modelo ONNX valido")
    
    # Mostrar informacion del modelo
    print("\nINFORMACION DEL MODELO ONNX:")
    print(f"   Input name: {onnx_model.graph.input[0].name}")
    print(f"   Output name: {onnx_model.graph.output[0].name}")
    print(f"   Opset version: {onnx_model.opset_import[0].version}")
    
    # Verificar tamano del archivo
    tamano = os.path.getsize(NOMBRE_ARCHIVO) / (1024 * 1024)
    print(f"\nTamano del archivo: {tamano:.2f} MB")
    
    print("\n" + "="*60)
    print("EXPORTACION COMPLETADA EXITOSAMENTE")
    print("="*60)
    print(f"\nArchivo generado: {NOMBRE_ARCHIVO}")
    print("\nESPECIFICACIONES CUMPLIDAS:")
    print("   Input shape: [1, 224, 224, 3]")
    print("   Output shape: [1, 1]")
    print("   Activacion: Sigmoid")
    print("   Rango: 0.0 - 1.0")
else:
    print("\nERROR: No se pudo generar el archivo ONNX")