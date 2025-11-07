# 🌐 Aplicación Web y TTS en Tiempo Real

## ✅ Sí, CoquiTTS incluye ambas características

### 🖥️ **Aplicación Web Incluida**

El repositorio incluye un **servidor web completo con interfaz gráfica**:

#### Características del Servidor Web:
- ✅ **Interfaz web amigable** (HTML + JavaScript)
- ✅ **API REST** para integración
- ✅ **Selección de modelos y voces**
- ✅ **Soporte multilingüe**
- ✅ **Clonación de voz** (con modelos compatibles)
- ✅ **Control de estilo** (GST tokens)
- ✅ **Compatible con MaryTTS API**

**Ubicación del código**:
- Servidor: `TTS/server/server.py:1`
- Interfaz web: `TTS/server/templates/index.html:1`

---

### ⚡ **TTS en Tiempo Real (Streaming)**

**¡SÍ!** El modelo **XTTS v2** incluye soporte para **streaming/generación en tiempo real**.

#### Características del Streaming:
- ✅ Genera audio **por chunks** en tiempo real
- ✅ Latencia ultra-baja (empieza a reproducir antes de terminar)
- ✅ Ideal para asistentes de voz y aplicaciones interactivas
- ✅ Control de tamaño de chunks
- ✅ Crossfading automático entre chunks

**Ubicación del código**:
- Implementación: `TTS/tts/models/xtts.py:611` (método `inference_stream`)
- Stream generator: `TTS/tts/layers/xtts/stream_generator.py:1`

---

## 🚀 Cómo Usar

### 1. Servidor Web Básico

#### Iniciar con Docker:
```bash
# Opción 1: Docker Compose (recomendado)
docker-compose up -d tts-server

# Opción 2: Docker directo
docker run --gpus all -d \
  -p 5002:5002 \
  --name tts-server \
  coqui-tts:latest \
  tts-server --host 0.0.0.0 --port 5002 --use_cuda true
```

#### Iniciar sin Docker:
```bash
# Con modelo pre-entrenado
tts-server --host 0.0.0.0 --port 5002 --use_cuda true

# Con modelo específico
tts-server \
  --model_name "tts_models/es/css10/vits" \
  --host 0.0.0.0 \
  --port 5002 \
  --use_cuda true
```

#### Acceder:
```
http://localhost:5002
```

---

### 2. API REST del Servidor

#### Generar Audio (GET):
```bash
curl "http://localhost:5002/api/tts?text=Hola%20mundo" --output audio.wav
```

#### Generar Audio (POST):
```bash
curl -X POST "http://localhost:5002/api/tts" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "text=Hola desde la API" \
  -d "speaker_id=speaker_01" \
  -d "language_id=es" \
  --output audio.wav
```

#### Usar desde JavaScript:
```javascript
// En tu aplicación web
fetch('/api/tts?text=' + encodeURIComponent('Hola mundo'))
  .then(response => response.blob())
  .then(blob => {
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play();
  });
```

#### Usar desde Python:
```python
import requests

response = requests.get(
    'http://localhost:5002/api/tts',
    params={
        'text': 'Hola desde Python',
        'speaker_id': 'speaker_01',
        'language_id': 'es'
    }
)

with open('output.wav', 'wb') as f:
    f.write(response.content)
```

---

### 3. TTS en Tiempo Real (Streaming)

⚠️ **Nota**: El servidor web actual **NO incluye streaming** por defecto. Aquí te muestro cómo implementarlo.

#### Script Python con Streaming:

```python
"""
Script para TTS con streaming en tiempo real usando XTTS v2
Guarda este archivo como: streaming_tts.py
"""

from TTS.api import TTS
import sounddevice as sd
import numpy as np
import torch

# Inicializar modelo XTTS v2 (necesario para streaming)
print("Cargando modelo XTTS v2...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

def stream_tts(text, language="es", speaker_wav=None):
    """
    Genera y reproduce audio en tiempo real

    Args:
        text: Texto a sintetizar
        language: Idioma (es, en, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja)
        speaker_wav: Archivo de referencia para clonar voz (opcional)
    """
    print(f"Generando: {text}")

    # Configurar modelo
    model = tts.synthesizer.tts_model

    # Obtener embeddings del speaker
    if speaker_wav:
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[speaker_wav],
            load_sr=model.config.audio.sample_rate
        )
    else:
        # Usar speaker por defecto
        gpt_cond_latent = tts.synthesizer.tts_model.get_cond_latents(
            audio_path=None
        )[0]
        speaker_embedding = tts.synthesizer.tts_model.get_speaker_embedding()

    # Stream en tiempo real
    chunks = []
    for chunk in model.inference_stream(
        text=text,
        language=language,
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
        stream_chunk_size=20,  # Tamaño de chunks (más pequeño = más rápido pero más overhead)
        enable_text_splitting=True
    ):
        # Convertir a numpy y reproducir inmediatamente
        chunk_audio = chunk.cpu().numpy()
        chunks.append(chunk_audio)

        # Reproducir chunk inmediatamente
        sd.play(chunk_audio, samplerate=24000)
        sd.wait()  # Esperar que termine este chunk

    # Guardar audio completo
    full_audio = np.concatenate(chunks)
    return full_audio

# Ejemplo de uso
if __name__ == "__main__":
    text = "Hola, esto es una demostración de texto a voz en tiempo real usando XTTS versión 2"

    # Sin clonación de voz
    audio = stream_tts(text, language="es")

    # Con clonación de voz (descomenta si tienes un archivo de referencia)
    # audio = stream_tts(text, language="es", speaker_wav="referencia.wav")

    print("¡Streaming completado!")
```

#### Servidor Flask con Streaming:

```python
"""
Servidor web con soporte para streaming
Guarda este archivo como: streaming_server.py
"""

from flask import Flask, Response, request, render_template_string
from TTS.api import TTS
import io

app = Flask(__name__)
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>TTS Streaming</title>
</head>
<body>
    <h1>🎤 TTS en Tiempo Real</h1>
    <textarea id="text" rows="5" cols="50" placeholder="Escribe aquí..."></textarea><br>
    <button onclick="streamTTS()">🎵 Generar Audio (Streaming)</button><br><br>
    <audio id="audio" controls></audio>

    <script>
        async function streamTTS() {
            const text = document.getElementById('text').value;
            const response = await fetch('/stream', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text, language: 'es'})
            });

            const blob = await response.blob();
            const audio = document.getElementById('audio');
            audio.src = URL.createObjectURL(blob);
            audio.play();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    text = data.get('text', '')
    language = data.get('language', 'es')

    # Generar con streaming
    def generate():
        model = tts.synthesizer.tts_model

        # Obtener embeddings
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=None
        )

        # Stream chunks
        for chunk in model.inference_stream(
            text=text,
            language=language,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            stream_chunk_size=20
        ):
            # Convertir chunk a bytes WAV
            chunk_bytes = chunk.cpu().numpy().tobytes()
            yield chunk_bytes

    return Response(generate(), mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)
```

#### Ejecutar:
```bash
# Instalar dependencias adicionales
pip install sounddevice

# Ejecutar script de streaming
python streaming_tts.py

# O ejecutar servidor con streaming
python streaming_server.py
# Acceder a http://localhost:5003
```

---

## 📊 Comparación: Normal vs Streaming

| Característica | Modo Normal | Modo Streaming |
|----------------|-------------|----------------|
| **Latencia inicial** | Alta (~3-8s) | Baja (~0.5-1s) |
| **Uso de RAM** | Todo en memoria | Chunks progresivos |
| **Reproducción** | Después de completar | Mientras genera |
| **Mejor para** | Archivos, batch | Tiempo real, chatbots |
| **Complejidad** | Simple | Moderada |
| **Modelos soportados** | Todos | Solo XTTS v2 |

---

## 🎯 Casos de Uso

### Servidor Web (No Streaming)
- ✅ Generar archivos de audio
- ✅ Síntesis batch
- ✅ Integración simple
- ✅ Cualquier modelo TTS

### Streaming (Tiempo Real)
- ✅ Asistentes de voz
- ✅ Chatbots interactivos
- ✅ Aplicaciones de accesibilidad
- ✅ Narración en vivo
- ✅ Videojuegos (diálogos dinámicos)

---

## 🔧 Configuración con Docker

### Dockerfile para Servidor con Streaming

Agrega a tu `docker-compose.yml`:

```yaml
services:
  # ... servicios existentes ...

  tts-streaming:
    build:
      context: .
      dockerfile: Dockerfile
    image: coqui-tts:latest
    container_name: coqui-tts-streaming

    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0

    volumes:
      - ./streaming_server.py:/workspace/streaming_server.py
      - ./models:/workspace/models

    ports:
      - "5003:5003"

    working_dir: /workspace
    command: ["python", "/workspace/streaming_server.py"]

    restart: unless-stopped
```

Luego ejecuta:
```bash
# Copiar el script al directorio
cp streaming_server.py ./

# Iniciar servidor de streaming
docker-compose up -d tts-streaming

# Acceder
# http://localhost:5003
```

---

## 📝 Resumen

### ✅ **Aplicación Web: SÍ**
- Servidor Flask incluido
- Interfaz web lista para usar
- API REST completa
- Puerto por defecto: 5002

### ✅ **TTS en Tiempo Real: SÍ**
- Solo con modelo XTTS v2
- Requiere implementación personalizada
- Latencia ultra-baja
- Scripts de ejemplo incluidos arriba

### 🚀 **Inicio Rápido**

```bash
# Servidor web básico
docker-compose up -d tts-server
# → http://localhost:5002

# Para streaming, usa los scripts Python mostrados arriba
```

---

## 🆘 Soporte

- **Código del servidor**: `TTS/server/server.py`
- **Código de streaming**: `TTS/tts/models/xtts.py` (línea 611)
- **Documentación**: [GUIA_INSTALACION.md](GUIA_INSTALACION.md)

¡Disfruta de CoquiTTS en tiempo real! 🎤✨
