# INO544-2026I-Carros

## Detector de Carros - Proyecto Universitario
### IUJO — Feria de Haceres Período I-2026

## Integrantes
- **Integrante 1:** [Beatriz Albornoz] - [30978113]
- **Integrante 2:** [Yodsan Alarcon] - [27279007] 
- **Integrante 3:** [Adrian Antoine] - [27795700]
- **Integrante 3:** [Cesar Colina] - [32088785]

## Tema
- **Objeto:** Carros
- **Descripción:** Modelo CNN para reconocer imágenes de carros

## Dataset
- Carros: 492 imágenes
- No carros: 358 imágenes
- Resolución: 224x224 píxeles, RGB

## Resultados
- Precisión en prueba: 94.53%
- Aciertos carros: 100%
- Aciertos no carros: 100%

## Especificaciones ONNX
- Input: [1, 224, 224, 3]
- Output: [1, 1]
- Activación: Sigmoid

## Cómo ejecutar
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python interfaz_carros.py