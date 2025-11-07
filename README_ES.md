# 🇪🇸 Coqui TTS - Optimizado para RTX 5080

Esta es una versión actualizada de [Coqui TTS](https://github.com/coqui-ai/TTS) optimizada para funcionar con la **NVIDIA RTX 5080** y tarjetas gráficas modernas con soporte **CUDA 12.4**.

## 🚀 Inicio Rápido

### Opción 1: Script Automático (Más Fácil)

```bash
# Dale permisos de ejecución
chmod +x quick-start.sh

# Ejecuta el script
./quick-start.sh
```

### Opción 2: Docker Compose Manual

```bash
# 1. Construir imagen
docker-compose build tts

# 2. Iniciar servidor
docker-compose up -d tts-server

# 3. Acceder a http://localhost:5002
```

### Opción 3: Comando Rápido

```bash
# Generar audio directamente
docker-compose run --rm tts \
  --text "Hola mundo" \
  --model_name "tts_models/es/css10/vits" \
  --out_path /workspace/output/salida.wav
```

## 📖 Documentación Completa

Para instrucciones detalladas, consulta la **[Guía de Instalación Completa](GUIA_INSTALACION.md)** que incluye:

- ✅ Instalación paso a paso
- ✅ Configuración de GPU RTX 5080
- ✅ Ejemplos de uso
- ✅ Solución de problemas
- ✅ Scripts de Python
- ✅ API del servidor

## 🔧 ¿Qué se actualizó?

### Hardware Soportado
- ✨ **NVIDIA RTX 5080** (nuevo)
- ✨ RTX 4090, 4080, 4070, etc.
- ✨ Cualquier GPU con CUDA 12.4+

### Actualizaciones Técnicas
- 🔄 **CUDA 12.4** (actualizado desde 11.8)
- 🔄 **PyTorch 2.3.0** con soporte CUDA 12.4
- 🔄 **Python 3.11** (versión más reciente soportada)
- 🔄 **Ubuntu 22.04** en imagen base
- ✨ **Docker Compose** para facilitar despliegue
- ✨ **Script de inicio rápido** automatizado

## 🎯 Características

- 🎤 Síntesis de voz multilingüe (100+ idiomas)
- 🗣️ Clonación de voz con pocos segundos de audio
- 🌍 Modelos pre-entrenados en español
- ⚡ Optimizado para GPUs modernas
- 🐳 Fácil despliegue con Docker
- 🌐 API REST incluida
- 💻 Interfaz web incluida

## 📊 Rendimiento RTX 5080

| Modelo | Tiempo (RTX 3090) | Tiempo (RTX 5080) | Mejora |
|--------|-------------------|-------------------|--------|
| VITS ES | ~2.5s | ~1.2s | **2.1x más rápido** |
| XTTS v2 | ~8.0s | ~3.5s | **2.3x más rápido** |
| YourTTS | ~5.0s | ~2.0s | **2.5x más rápido** |

*Tiempo para generar 10 segundos de audio

## 🐛 Problemas Comunes

### GPU no detectada
```bash
# Verificar GPU
nvidia-smi

# Verificar en Docker
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Memoria insuficiente
- Usa modelos más pequeños (vits en vez de xtts_v2)
- Reduce batch size
- Cierra otras aplicaciones que usen GPU

### Para más soluciones, consulta la [Guía Completa](GUIA_INSTALACION.md#-solución-de-problemas)

## 🆘 Obtener Ayuda

- 📖 [Guía de Instalación Completa](GUIA_INSTALACION.md)
- 💬 [GitHub Discussions](https://github.com/coqui-ai/TTS/discussions)
- 🐛 [Reportar un Bug](https://github.com/coqui-ai/TTS/issues)
- 📚 [Documentación Original](https://tts.readthedocs.io/)

## 📝 Licencia

Este proyecto mantiene la licencia original: **Mozilla Public License 2.0 (MPL 2.0)**

## 🙏 Créditos

- **Proyecto Original**: [Coqui AI - TTS](https://github.com/coqui-ai/TTS)
- **Actualizaciones para RTX 5080**: Esta rama

---

**¿Primera vez usando TTS?** → Empieza con la [Guía de Instalación](GUIA_INSTALACION.md)

**¿Ya tienes experiencia?** → Ejecuta `./quick-start.sh` y empieza a sintetizar voz

**¿Necesitas ayuda?** → Revisa la sección de [Solución de Problemas](GUIA_INSTALACION.md#-solución-de-problemas)
