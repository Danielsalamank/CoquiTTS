# 🇪🇸 Guía de Instalación - Coqui TTS para RTX 5080

Esta guía te ayudará a configurar Coqui TTS optimizado para tu NVIDIA RTX 5080 usando Docker.

## 📋 Requisitos Previos

### Hardware
- **GPU**: NVIDIA RTX 5080 (o cualquier GPU compatible con CUDA 12.4+)
- **RAM**: Mínimo 16GB recomendado
- **Espacio en disco**: Al menos 10GB libres

### Software
1. **Sistema Operativo**: Ubuntu 20.04/22.04, Windows 11 con WSL2, o macOS (solo CPU)
2. **Drivers NVIDIA**: Versión 550.54.15 o superior
3. **Docker**: Versión 20.10 o superior
4. **NVIDIA Container Toolkit**: Para soporte GPU en Docker

---

## 🔧 Instalación de Requisitos

### 1. Instalar Docker

#### Ubuntu/Debian:
```bash
# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Añadir usuario al grupo docker (evita usar sudo)
sudo usermod -aG docker $USER
newgrp docker
```

#### Windows:
1. Descargar e instalar [Docker Desktop para Windows](https://www.docker.com/products/docker-desktop)
2. Habilitar WSL2 backend
3. Reiniciar el sistema

### 2. Instalar NVIDIA Container Toolkit

```bash
# Configurar repositorio
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Instalar
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configurar Docker para usar NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3. Verificar Instalación de GPU

```bash
# Verificar drivers NVIDIA
nvidia-smi

# Deberías ver algo como:
# +-----------------------------------------------------------------------------------------+
# | NVIDIA-SMI 550.54.15              Driver Version: 550.54.15      CUDA Version: 12.4     |
# |---------- --------------------+----------------------+----------------------+
# | GPU  Name                 ...  | RTX 5080           |                      |
```

---

## 🚀 Instalación con Docker (Recomendado)

### Opción 1: Usar Docker Compose (Más Fácil)

1. **Clonar el repositorio** (si aún no lo has hecho):
```bash
git clone https://github.com/coqui-ai/TTS.git
cd TTS
```

2. **Crear directorios necesarios**:
```bash
mkdir -p models output data
```

3. **Construir la imagen Docker**:
```bash
docker-compose build tts
```

4. **Verificar que funciona**:
```bash
# Ver opciones disponibles
docker-compose run --rm tts --help

# Listar modelos disponibles
docker-compose run --rm tts --list_models
```

5. **Iniciar el servidor TTS**:
```bash
# Iniciar servidor en segundo plano
docker-compose up -d tts-server

# Ver logs
docker-compose logs -f tts-server
```

El servidor estará disponible en: `http://localhost:5002`

### Opción 2: Usar Docker directamente

1. **Construir la imagen**:
```bash
docker build -t coqui-tts:latest .
```

2. **Ejecutar comandos TTS**:
```bash
# Ver ayuda
docker run --gpus all --rm coqui-tts:latest --help

# Listar modelos
docker run --gpus all --rm coqui-tts:latest --list_models

# Generar audio
docker run --gpus all --rm \
  -v $(pwd)/output:/workspace/output \
  coqui-tts:latest \
  --text "Hola, esto es una prueba con mi RTX 5080" \
  --model_name "tts_models/es/css10/vits" \
  --out_path /workspace/output/salida.wav
```

3. **Iniciar servidor**:
```bash
docker run --gpus all -d \
  -p 5002:5002 \
  -v $(pwd)/models:/workspace/models \
  -v $(pwd)/output:/workspace/output \
  --name coqui-tts-server \
  coqui-tts:latest \
  tts-server --host 0.0.0.0 --port 5002
```

---

## 💻 Instalación Sin Docker

### 1. Instalar Python 3.11

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-dev python3.11-venv
```

### 2. Crear Entorno Virtual

```bash
# Crear entorno
python3.11 -m venv venv

# Activar entorno
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar CUDA Toolkit 12.4

```bash
# Ubuntu/Debian
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-4
```

### 4. Instalar Dependencias del Sistema

```bash
sudo apt-get install -y \
    espeak-ng \
    libsndfile1-dev \
    gcc \
    g++ \
    make
```

### 5. Instalar PyTorch con CUDA 12.4

```bash
pip install torch==2.3.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu124
```

### 6. Instalar Coqui TTS

```bash
# Instalar desde el repositorio local
pip install -e .

# O instalar desde PyPI (puede no tener las últimas actualizaciones)
# pip install TTS
```

### 7. Verificar Instalación

```bash
# Verificar que PyTorch detecta la GPU
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No disponible"}')"

# Deberías ver:
# CUDA disponible: True
# GPU: NVIDIA GeForce RTX 5080
```

---

## 🎯 Uso Básico

### Desde la Línea de Comandos

```bash
# Listar todos los modelos disponibles
tts --list_models

# Generar audio con modelo en español
tts --text "Hola mundo, esta es mi voz sintética" \
    --model_name "tts_models/es/css10/vits" \
    --out_path salida.wav

# Generar audio con modelo multilingüe
tts --text "Hello world, this is my synthetic voice" \
    --model_name "tts_models/multilingual/multi-dataset/xtts_v2" \
    --language_idx "en" \
    --out_path output_en.wav

# Clonar voz (requiere archivo de referencia)
tts --text "Quiero clonar esta voz" \
    --model_name "tts_models/multilingual/multi-dataset/xtts_v2" \
    --language_idx "es" \
    --speaker_wav referencia.wav \
    --out_path clonada.wav
```

### Usando el Servidor Web

1. **Iniciar servidor**:
```bash
# Con Docker Compose
docker-compose up tts-server

# Sin Docker
tts-server --host 0.0.0.0 --port 5002
```

2. **Acceder a la interfaz web**:
   - Abrir navegador en: `http://localhost:5002`
   - Seleccionar modelo
   - Escribir texto
   - Generar audio

3. **Usar la API**:
```bash
# Ejemplo con curl
curl -X POST http://localhost:5002/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola desde la API",
    "model_name": "tts_models/es/css10/vits"
  }' \
  --output resultado.wav
```

### Desde Python

```python
from TTS.api import TTS

# Inicializar TTS con modelo en español
tts = TTS(model_name="tts_models/es/css10/vits", gpu=True)

# Generar audio
tts.tts_to_file(
    text="Hola, esto es una prueba desde Python",
    file_path="salida_python.wav"
)

# Usar modelo multilingüe
tts_multi = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

tts_multi.tts_to_file(
    text="Esto es una prueba en español",
    file_path="multi_es.wav",
    language="es"
)

# Clonar voz
tts_multi.tts_to_file(
    text="Clonando una voz",
    file_path="voz_clonada.wav",
    speaker_wav="referencia.wav",
    language="es"
)
```

---

## 🔍 Verificar que la RTX 5080 se está Usando

### Durante la ejecución, verifica el uso de GPU:

```bash
# En otra terminal, ejecuta:
watch -n 1 nvidia-smi

# Deberías ver:
# - GPU-Util al 80-100% cuando genera audio
# - Memoria GPU en uso
# - Proceso "python" o "tts" listado
```

### Desde Python:

```python
import torch

print(f"CUDA disponible: {torch.cuda.is_available()}")
print(f"Dispositivo actual: {torch.cuda.current_device()}")
print(f"Nombre GPU: {torch.cuda.get_device_name(0)}")
print(f"Memoria GPU total: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
```

---

## 🐛 Solución de Problemas

### Error: "CUDA out of memory"

**Solución**:
```python
# Reducir tamaño de batch o usar modelos más pequeños
# En docker-compose.yml, limitar memoria GPU:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1  # Usar solo 1 GPU
          capabilities: [gpu]
```

### Error: "nvidia-smi: command not found"

**Solución**:
```bash
# Instalar drivers NVIDIA
sudo ubuntu-drivers autoinstall
sudo reboot
```

### Error: "Docker: no matching manifest for linux/arm64"

**Solución**: Estás en arquitectura ARM (Mac M1/M2). Usa imágenes CPU:
```bash
# Editar Dockerfile, cambiar BASE a:
ARG BASE=ubuntu:22.04
# Y eliminar instalación de CUDA
```

### La GPU no se detecta en Docker

**Solución**:
```bash
# Re-configurar NVIDIA Container Toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verificar configuración
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Audio con calidad pobre

**Soluciones**:
1. Usar modelos más grandes (xtts_v2 vs vits)
2. Ajustar parámetros de síntesis
3. Proporcionar mejor audio de referencia para clonación

### Errores con modelos en español

**Solución**:
```bash
# Instalar dependencias adicionales para español
pip install unidecode phonemizer

# Verificar espeak-ng
espeak-ng --voices=es
```

---

## 📊 Modelos Recomendados para Español

| Modelo | Calidad | Velocidad | Clonación | Uso RAM GPU |
|--------|---------|-----------|-----------|-------------|
| `tts_models/es/css10/vits` | Media | Rápida | No | ~2GB |
| `tts_models/es/mai/tacotron2-DDC` | Media | Media | No | ~3GB |
| `tts_models/multilingual/multi-dataset/xtts_v2` | Alta | Lenta | Sí | ~6GB |
| `tts_models/multilingual/multi-dataset/your_tts` | Alta | Media | Sí | ~4GB |

---

## 🎨 Ejemplos Avanzados

### Script de Procesamiento por Lotes

```python
# batch_tts.py
from TTS.api import TTS
import os

# Inicializar
tts = TTS(model_name="tts_models/es/css10/vits", gpu=True)

# Textos a procesar
textos = [
    "Primera frase a sintetizar",
    "Segunda frase a sintetizar",
    "Tercera frase a sintetizar"
]

# Generar todos
for i, texto in enumerate(textos):
    output_path = f"salida_{i:03d}.wav"
    tts.tts_to_file(text=texto, file_path=output_path)
    print(f"Generado: {output_path}")
```

### Servidor Flask Personalizado

```python
# servidor_custom.py
from flask import Flask, request, send_file
from TTS.api import TTS
import tempfile
import os

app = Flask(__name__)
tts = TTS(model_name="tts_models/es/css10/vits", gpu=True)

@app.route('/generar', methods=['POST'])
def generar_audio():
    texto = request.json.get('texto', '')

    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        tts.tts_to_file(text=texto, file_path=tmp.name)
        return send_file(tmp.name, mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
```

---

## 📚 Recursos Adicionales

- **Documentación oficial**: https://tts.readthedocs.io/
- **Modelos pre-entrenados**: https://github.com/coqui-ai/TTS#pretrained-models
- **Foro de la comunidad**: https://github.com/coqui-ai/TTS/discussions
- **Reportar bugs**: https://github.com/coqui-ai/TTS/issues

---

## ✅ Checklist de Instalación

- [ ] Drivers NVIDIA 550+ instalados
- [ ] `nvidia-smi` muestra la RTX 5080
- [ ] Docker instalado y funcionando
- [ ] NVIDIA Container Toolkit instalado
- [ ] Imagen Docker construida exitosamente
- [ ] `docker-compose run --rm tts --list_models` funciona
- [ ] Servidor TTS accesible en http://localhost:5002
- [ ] Audio generado correctamente
- [ ] GPU visible durante generación (`nvidia-smi`)

---

## 🎉 ¡Listo!

Ahora tienes Coqui TTS completamente configurado y optimizado para tu RTX 5080.

**Comandos rápidos para empezar**:
```bash
# Iniciar servidor
docker-compose up -d tts-server

# Generar audio rápido
docker-compose run --rm tts \
  --text "Mi primera síntesis de voz con RTX 5080" \
  --model_name "tts_models/es/css10/vits" \
  --out_path /workspace/output/prueba.wav

# Ver logs
docker-compose logs -f tts-server
```

¡Disfruta sintetizando voz! 🎤
