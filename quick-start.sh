#!/bin/bash
# Script de inicio rápido para Coqui TTS con Docker
# Para RTX 5080 con CUDA 12.4

set -e

echo "🎤 Coqui TTS - Script de Inicio Rápido para RTX 5080"
echo "=================================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar comandos
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ Error: $1 no está instalado${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $1 encontrado${NC}"
        return 0
    fi
}

# Verificar requisitos
echo "📋 Verificando requisitos..."
check_command docker || { echo "Instala Docker primero: https://docs.docker.com/get-docker/"; exit 1; }
check_command nvidia-smi || { echo "Instala drivers NVIDIA primero"; exit 1; }

# Verificar GPU
echo ""
echo "🎮 Verificando GPU..."
GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
echo -e "${GREEN}GPU detectada: $GPU_INFO${NC}"

# Verificar NVIDIA Container Toolkit
echo ""
echo "🐳 Verificando NVIDIA Container Toolkit..."
if docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA Container Toolkit funcionando correctamente${NC}"
else
    echo -e "${RED}❌ Error: NVIDIA Container Toolkit no configurado${NC}"
    echo "Ejecuta: sudo apt-get install -y nvidia-container-toolkit"
    echo "Luego: sudo nvidia-ctk runtime configure --runtime=docker"
    echo "Y reinicia Docker: sudo systemctl restart docker"
    exit 1
fi

# Crear directorios necesarios
echo ""
echo "📁 Creando directorios..."
mkdir -p models output data
echo -e "${GREEN}✓ Directorios creados${NC}"

# Menú de opciones
echo ""
echo "¿Qué deseas hacer?"
echo "1) Construir imagen Docker"
echo "2) Iniciar servidor TTS"
echo "3) Generar audio de prueba"
echo "4) Listar modelos disponibles"
echo "5) Todo lo anterior (setup completo)"
echo ""
read -p "Selecciona una opción (1-5): " option

case $option in
    1)
        echo ""
        echo "🔨 Construyendo imagen Docker..."
        docker-compose build tts
        echo -e "${GREEN}✓ Imagen construida exitosamente${NC}"
        ;;
    2)
        echo ""
        echo "🚀 Iniciando servidor TTS..."
        docker-compose up -d tts-server
        echo -e "${GREEN}✓ Servidor iniciado en http://localhost:5002${NC}"
        echo "Ver logs con: docker-compose logs -f tts-server"
        ;;
    3)
        echo ""
        echo "🎵 Generando audio de prueba..."
        docker-compose run --rm tts \
            --text "Hola, esta es una prueba con mi RTX 5080" \
            --model_name "tts_models/es/css10/vits" \
            --out_path /workspace/output/prueba.wav
        echo -e "${GREEN}✓ Audio generado en: ./output/prueba.wav${NC}"
        ;;
    4)
        echo ""
        echo "📋 Listando modelos disponibles..."
        docker-compose run --rm tts --list_models
        ;;
    5)
        echo ""
        echo "🔨 Construyendo imagen Docker..."
        docker-compose build tts

        echo ""
        echo "📋 Listando modelos disponibles..."
        docker-compose run --rm tts --list_models | head -n 20

        echo ""
        echo "🎵 Generando audio de prueba..."
        docker-compose run --rm tts \
            --text "Hola, esta es una prueba con mi RTX 5080" \
            --model_name "tts_models/es/css10/vits" \
            --out_path /workspace/output/prueba.wav

        echo ""
        echo "🚀 Iniciando servidor TTS..."
        docker-compose up -d tts-server

        echo ""
        echo -e "${GREEN}✅ ¡Setup completo!${NC}"
        echo ""
        echo "Servidor TTS: http://localhost:5002"
        echo "Audio de prueba: ./output/prueba.wav"
        echo "Ver logs: docker-compose logs -f tts-server"
        ;;
    *)
        echo -e "${RED}Opción inválida${NC}"
        exit 1
        ;;
esac

echo ""
echo "✨ ¡Listo! Consulta GUIA_INSTALACION.md para más información"
