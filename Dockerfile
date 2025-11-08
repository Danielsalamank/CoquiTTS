# Dockerfile optimizado para RTX 5080 con CUDA 12.4
ARG BASE=nvidia/cuda:12.4.0-runtime-ubuntu22.04
FROM ${BASE}

# Establecer variables de entorno para CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Actualizar sistema e instalar dependencias
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    python3-wheel \
    espeak-ng \
    libsndfile1-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Crear enlace simbólico para python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python

# Actualizar pip
RUN python -m pip install --upgrade pip setuptools wheel

# Instalar PyTorch con soporte CUDA 12.4 (versiones disponibles en cu124)
# Se actualiza a una versión compatible ya que 2.3.0 no está disponible en cu124
RUN pip3 install --index-url https://download.pytorch.org/whl/cu124 \
    torch==2.5.1+cu124 torchaudio==2.5.1+cu124

# Instalar llvmlite primero
RUN pip3 install llvmlite --ignore-installed

# Copiar archivos del repositorio
WORKDIR /workspace/TTS
COPY . /workspace/TTS

# Instalar TTS y dependencias
RUN pip3 install -e . && \
    rm -rf /root/.cache/pip

# Crear directorio para modelos y datos
RUN mkdir -p /workspace/models /workspace/output

# Exponer puerto para servidor TTS
EXPOSE 5002

# Punto de entrada
ENTRYPOINT ["tts"]
CMD ["--help"]
