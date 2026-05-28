# ==============================================
# ENTRENAMIENTO SIMPLE - PARA POCAS IMAGENES
# ==============================================

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import random

print("="*60)
print("ENTRENAMIENTO SIMPLE - ANTI-OVERFITTING")
print("="*60)


# CONFIGURACION
RUTA_CARROS = r"C:\Users\beatr\OneDrive\Desktop\dataset_aumentado"
RUTA_NO_CARROS = r"C:\Users\beatr\OneDrive\Desktop\no_carros"

def cargar_imagenes(ruta_carros, ruta_no_carros):
    imagenes = []
    etiquetas = []
    
    print("\nCargando CARROS...")
    archivos_carros = [f for f in os.listdir(ruta_carros) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    for archivo in archivos_carros:
        ruta = os.path.join(ruta_carros, archivo)
        try:
            img = tf.keras.preprocessing.image.load_img(ruta, target_size=(224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
            imagenes.append(img_array)
            etiquetas.append(1)
        except:
            pass
    
    print(f"   {len([e for e in etiquetas if e == 1])} carros")
    
    print("\nCargando NO CARROS...")
    archivos_no_carros = [f for f in os.listdir(ruta_no_carros) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    for archivo in archivos_no_carros:
        ruta = os.path.join(ruta_no_carros, archivo)
        try:
            img = tf.keras.preprocessing.image.load_img(ruta, target_size=(224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
            imagenes.append(img_array)
            etiquetas.append(0)
        except:
            pass
    
    print(f"   {len([e for e in etiquetas if e == 0])} no carros")
    
    return np.array(imagenes), np.array(etiquetas)

# Cargar datos
X, y = cargar_imagenes(RUTA_CARROS, RUTA_NO_CARROS)

print(f"\nTOTAL: {len(X)} imagenes")
print(f"   CARROS: {sum(y)}")
print(f"   NO CARROS: {len(y) - sum(y)}")

# Mezclar
indices = list(range(len(X)))
random.shuffle(indices)
X = X[indices]
y = y[indices]

# Dividir
n = len(X)
train_end = int(0.7 * n)
val_end = int(0.85 * n)

X_train, y_train = X[:train_end], y[:train_end]
X_val, y_val = X[train_end:val_end], y[train_end:val_end]
X_test, y_test = X[val_end:], y[val_end:]

print(f"\nDIVISION:")
print(f"   Entrenamiento: {len(X_train)}")
print(f"   Validacion: {len(X_val)}")
print(f"   Prueba: {len(X_test)}")

# Aumento de datos para variedad
datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.15,
    height_shift_range=0.15,
    zoom_range=0.15,
    horizontal_flip=True,
    fill_mode='nearest'
)

# MODELO MAS SIMPLE (menos capas)
print("\nCREANDO MODELO SIMPLE...")

model = keras.Sequential([
    layers.Input(shape=(224, 224, 3)),
    
    # Solo 2 bloques convolucionales
    layers.Conv2D(16, (3, 3), activation='relu'),
    layers.MaxPooling2D(2, 2),
    
    layers.Conv2D(32, (3, 3), activation='relu'),
    layers.MaxPooling2D(2, 2),
    
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D(2, 2),
    
    layers.Flatten(),
    layers.Dropout(0.5),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(1, activation='sigmoid')
])

# Learning rate mas bajo
optimizer = keras.optimizers.Adam(learning_rate=0.0001)

model.compile(
    optimizer=optimizer,
    loss='binary_crossentropy',
    metrics=['accuracy']
)

model.summary()

# Callbacks
callbacks = [
    keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
    keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3)
]

# Entrenar
print("\nINICIANDO ENTRENAMIENTO...")

history = model.fit(
    datagen.flow(X_train, y_train, batch_size=16, shuffle=True),
    epochs=30,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1
)

# Evaluar
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
print(f"\nPRECISION EN PRUEBA: {test_acc * 100:.2f}%")

# Guardar
model.save("modelo_carros.h5")
print("modelo_carros.h5 guardado")

# Probar
print("\n" + "="*60)
print("PRUEBA FINAL")
print("="*60)

def probar(ruta):
    img = tf.keras.preprocessing.image.load_img(ruta, target_size=(224, 224))
    img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return model.predict(img_array, verbose=0)[0][0]

print("\n--- CARROS (deben dar >0.5) ---")
carros = [f for f in os.listdir(RUTA_CARROS) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:20]
aciertos_carros = 0
for archivo in carros:
    ruta = os.path.join(RUTA_CARROS, archivo)
    valor = probar(ruta)
    acierto = valor > 0.5
    if acierto:
        aciertos_carros += 1
    estado = "BIEN" if acierto else "MAL"
    print(f"   {estado} {archivo}: {valor:.4f}")

print(f"\n   ACIERTOS CARROS: {aciertos_carros}/{len(carros)} ({aciertos_carros/len(carros)*100:.1f}%)")

print("\n--- NO CARROS (deben dar <0.5) ---")
no_carros = [f for f in os.listdir(RUTA_NO_CARROS) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:20]
aciertos_no_carros = 0
for archivo in no_carros:
    ruta = os.path.join(RUTA_NO_CARROS, archivo)
    valor = probar(ruta)
    acierto = valor < 0.5
    if acierto:
        aciertos_no_carros += 1
    estado = "BIEN" if acierto else "MAL"
    print(f"   {estado} {archivo}: {valor:.4f}")

print(f"\n   ACIERTOS NO CARROS: {aciertos_no_carros}/{len(no_carros)} ({aciertos_no_carros/len(no_carros)*100:.1f}%)")

print("\n" + "="*60)
print(f"PRECISION TOTAL: {(aciertos_carros + aciertos_no_carros) / (len(carros) + len(no_carros)) * 100:.1f}%")
print("="*60)