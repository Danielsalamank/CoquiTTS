#!flask/bin/python
import argparse
import io
import json
import os
import sys
import time
import subprocess
from pathlib import Path
from threading import Lock, Thread
from typing import Union
from urllib.parse import parse_qs

from flask import Flask, render_template, render_template_string, request, send_file, jsonify

from TTS.config import load_config
from TTS.utils.manage import ModelManager
from TTS.utils.synthesizer import Synthesizer


def create_argparser():
    def convert_boolean(x):
        return x.lower() in ["true", "1", "yes"]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list_models",
        type=convert_boolean,
        nargs="?",
        const=True,
        default=False,
        help="list available pre-trained tts and vocoder models.",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="tts_models/en/ljspeech/tacotron2-DDC",
        help="Name of one of the pre-trained tts models in format <language>/<dataset>/<model_name>",
    )
    parser.add_argument("--vocoder_name", type=str, default=None, help="name of one of the released vocoder models.")

    # Args for running custom models
    parser.add_argument("--config_path", default=None, type=str, help="Path to model config file.")
    parser.add_argument(
        "--model_path",
        type=str,
        default=None,
        help="Path to model file.",
    )
    parser.add_argument(
        "--vocoder_path",
        type=str,
        help="Path to vocoder model file. If it is not defined, model uses GL as vocoder. Please make sure that you installed vocoder library before (WaveRNN).",
        default=None,
    )
    parser.add_argument("--vocoder_config_path", type=str, help="Path to vocoder model config file.", default=None)
    parser.add_argument("--speakers_file_path", type=str, help="JSON file for multi-speaker model.", default=None)
    parser.add_argument("--port", type=int, default=5002, help="port to listen on.")
    parser.add_argument("--use_cuda", type=convert_boolean, default=False, help="true to use CUDA.")
    parser.add_argument("--debug", type=convert_boolean, default=False, help="true to enable Flask debug mode.")
    parser.add_argument("--show_details", type=convert_boolean, default=False, help="Generate model detail page.")
    return parser


args = create_argparser().parse_args()

app = Flask(__name__)

# CORS básico para integraciones (n8n, frontend externo)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# Globals initialized lazily to prevent long startup blocking
path = Path(__file__).parent / "../.models.json"
manager = ModelManager(path)
synthesizer = None
speaker_manager = None
language_manager = None
use_multi_speaker = False
use_multi_language = False

def _load_models_async():
    global synthesizer, speaker_manager, language_manager, use_multi_language, use_multi_speaker

    # update in-use models to the specified released models.
    model_path = None
    config_path = None
    speakers_file_path = None
    vocoder_path = None
    vocoder_config_path = None

    # CASE1: list pre-trained TTS models
    if args.list_models:
        manager.list_models()
        return

    # CASE2: load pre-trained model paths
    if args.model_name is not None and not args.model_path:
        model_path, config_path, model_item = manager.download_model(args.model_name)
        args.vocoder_name = model_item["default_vocoder"] if args.vocoder_name is None else args.vocoder_name

    if args.vocoder_name is not None and not args.vocoder_path:
        vocoder_path, vocoder_config_path, _ = manager.download_model(args.vocoder_name)

    # CASE3: set custom model paths
    if args.model_path is not None:
        model_path = args.model_path
        config_path = args.config_path
        speakers_file_path = args.speakers_file_path

    if args.vocoder_path is not None:
        vocoder_path = args.vocoder_path
        vocoder_config_path = args.vocoder_config_path

    synthesizer = Synthesizer(
        tts_checkpoint=model_path,
        tts_config_path=config_path,
        tts_speakers_file=speakers_file_path,
        tts_languages_file=None,
        vocoder_checkpoint=vocoder_path,
        vocoder_config=vocoder_config_path,
        encoder_checkpoint="",
        encoder_config="",
        use_cuda=args.use_cuda,
    )

    use_multi_speaker = hasattr(synthesizer.tts_model, "num_speakers") and (
        synthesizer.tts_model.num_speakers > 1 or synthesizer.tts_speakers_file is not None
    )
    speaker_manager = getattr(synthesizer.tts_model, "speaker_manager", None)

    use_multi_language = hasattr(synthesizer.tts_model, "num_languages") and (
        synthesizer.tts_model.num_languages > 1 or synthesizer.tts_languages_file is not None
    )
    language_manager = getattr(synthesizer.tts_model, "language_manager", None)

# TODO: set this from SpeakerManager
use_gst = False
def _get_use_gst():
    global use_gst
    try:
        if synthesizer is not None:
            use_gst = synthesizer.tts_config.get("use_gst", False)
    except Exception:
        use_gst = False
    return use_gst

# Start loading in background so API can come up quickly
Thread(target=_load_models_async, daemon=True).start()


def style_wav_uri_to_dict(style_wav: str) -> Union[str, dict]:
    """Transform an uri style_wav, in either a string (path to wav file to be use for style transfer)
    or a dict (gst tokens/values to be use for styling)

    Args:
        style_wav (str): uri

    Returns:
        Union[str, dict]: path to file (str) or gst style (dict)
    """
    if style_wav:
        if os.path.isfile(style_wav) and style_wav.endswith(".wav"):
            return style_wav  # style_wav is a .wav file located on the server

        style_wav = json.loads(style_wav)
        return style_wav  # style_wav is a gst dictionary with {token1_id : token1_weigth, ...}
    return None


@app.route("/")
def index():
    return render_template(
        "index.html",
        show_details=args.show_details,
        use_multi_speaker=use_multi_speaker,
        use_multi_language=use_multi_language,
        speaker_ids=speaker_manager.name_to_id if speaker_manager is not None else None,
        language_ids=language_manager.name_to_id if language_manager is not None else None,
        use_gst=_get_use_gst(),
    )


@app.route("/details")
def details():
    if args.config_path is not None and os.path.isfile(args.config_path):
        model_config = load_config(args.config_path)
    else:
        if args.model_name is not None:
            model_config = load_config(config_path)

    if args.vocoder_config_path is not None and os.path.isfile(args.vocoder_config_path):
        vocoder_config = load_config(args.vocoder_config_path)
    else:
        if args.vocoder_name is not None:
            vocoder_config = load_config(vocoder_config_path)
        else:
            vocoder_config = None

    return render_template(
        "details.html",
        show_details=args.show_details,
        model_config=model_config,
        vocoder_config=vocoder_config,
        args=args.__dict__,
    )


lock = Lock()
train_lock = Lock()
training_state = {
    "running": False,
    "process": None,
    "log_path": None,
    "start_time": None,
    "params": None,
}


@app.route("/api/tts", methods=["GET", "POST"])
def tts():
    if synthesizer is None:
        return jsonify({"error": "Modelo cargando, intenta de nuevo en unos segundos"}), 503
    with lock:
        text = request.headers.get("text") or request.values.get("text", "")
        speaker_idx = request.headers.get("speaker-id") or request.values.get("speaker_id", "")
        language_idx = request.headers.get("language-id") or request.values.get("language_id", "")
        style_wav = request.headers.get("style-wav") or request.values.get("style_wav", "")
        speaker_wav = request.headers.get("speaker-wav") or request.values.get("speaker_wav", "")
        style_wav = style_wav_uri_to_dict(style_wav)

        print(f" > Model input: {text}")
        if speaker_idx:
            print(f" > Speaker Idx: {speaker_idx}")
        if language_idx:
            print(f" > Language Idx: {language_idx}")

        # Solo pasamos speaker/language si el modelo lo soporta
        tts_kwargs = {}
        # Si llega speaker_id desde la UI/API, pásalo como speaker_name (coincide con Synthesizer.tts)
        if speaker_idx:
            tts_kwargs["speaker_name"] = speaker_idx
        # Si llega speaker_wav (XTTS), pásalo directamente
        if speaker_wav:
            tts_kwargs["speaker_wav"] = speaker_wav
        # Fallback: si el modelo es multi-speaker y no llega speaker, usa el primero disponible
        if not speaker_idx and use_multi_speaker and speaker_manager is not None:
            try:
                names = getattr(speaker_manager, "speaker_names", None)
                if names:
                    tts_kwargs["speaker_name"] = names[0]
            except Exception:
                pass
        # XTTS requiere language incluso si no hay language_manager expuesto
        if language_idx:
            model_str = args.model_name or ""
            if use_multi_language or ("xtts" in model_str or "multilingual" in model_str):
                tts_kwargs["language_name"] = language_idx

        # Validación específica para XTTS: requiere language y speaker_wav
        model_str = args.model_name or ""
        is_xtts = ("xtts" in model_str or "multilingual" in model_str)
        if is_xtts and not speaker_wav:
            return jsonify({
                "error": "XTTS requiere 'speaker_wav' (audio de referencia) y 'language_id'",
                "hint": "Proporcione ?speaker_wav=URL o cargue audio en la UI",
            }), 400

        try:
            wavs = synthesizer.tts(text, style_wav=style_wav, **tts_kwargs)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Fallo interno en TTS: {e}"}), 500
        out = io.BytesIO()
        synthesizer.save_wav(wavs, out)
    return send_file(out, mimetype="audio/wav")


@app.route("/api/languages", methods=["GET"])
def api_languages():
    # Mapa de códigos a etiquetas amigables
    lang_labels = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "tr": "Turkish",
        "pl": "Polish",
        "nl": "Dutch",
        "ar": "Arabic",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
    }

    if language_manager is not None and hasattr(language_manager, "name_to_id"):
        names_obj = language_manager.name_to_id
        if isinstance(names_obj, dict):
            codes = list(names_obj.keys())
        else:
            try:
                codes = list(names_obj)
            except Exception:
                codes = []
        languages = [{"id": str(c), "label": lang_labels.get(str(c), str(c))} for c in codes]
    else:
        # Fallback: si el modelo es multilenguaje (XTTS), devolvemos lista amplia
        model_str = args.model_name or ""
        if "multilingual" in model_str or "xtts" in model_str:
            codes = [
                "en","es","fr","de","it","pt","ru","tr","pl","nl","ar","zh","ja","ko"
            ]
            languages = [{"id": c, "label": lang_labels.get(c, c)} for c in codes]
        else:
            # caso monolingüe
            if args.model_name is not None:
                parts = args.model_name.split("/")
                code = parts[1] if len(parts) > 1 else "en"
            else:
                code = "en"
            languages = [{"id": code, "label": lang_labels.get(code, code)}]
    return jsonify({"languages": languages})


@app.route("/api/voices", methods=["GET"])
def api_voices():
    # Mapa de códigos VCTK a nombres amigables en español
    vctk_labels = {
        "p225": "Carlos (Male)",
        "p226": "Carmen (Female)",
        "p227": "Diego (Male)",
        "p228": "Isabel (Female)",
        "p229": "Javier (Male)",
        "p230": "José (Male)",
        "p231": "Lucía (Female)",
        "p232": "María (Female)",
        "p233": "Miguel (Male)",
        "p234": "Sofía (Female)",
    }

    # Leer idioma solicitado
    requested_language = request.args.get("language")

    try:
        # Si el modelo expone speakers reales, devolvemos esa lista directamente
        if speaker_manager is not None and hasattr(speaker_manager, "name_to_id"):
            names_obj = speaker_manager.name_to_id
            if isinstance(names_obj, dict):
                codes = list(names_obj.keys())
            else:
                try:
                    codes = list(names_obj)  # puede ser dict_keys o similar
                except Exception:
                    codes = []
            # Sanear entradas que vienen con saltos de línea u otros caracteres
            codes = [str(c).strip() for c in codes]
            voices = [{"id": c, "label": vctk_labels.get(c, c)} for c in codes]
        else:
            # No hay lista de speakers. Generamos voces por idioma para la UI.
            fallback_by_lang = {
                "en": [
                    {"id": "alex", "label": "Alex (Male)"},
                    {"id": "sofia", "label": "Sofia (Female)"},
                ],
                "es": [
                    {"id": "carlos", "label": "Carlos (Male)"},
                    {"id": "carmen", "label": "Carmen (Female)"},
                ],
                "fr": [
                    {"id": "luc", "label": "Luc (Male)"},
                    {"id": "marie", "label": "Marie (Female)"},
                ],
                "de": [
                    {"id": "hans", "label": "Hans (Male)"},
                    {"id": "anna", "label": "Anna (Female)"},
                ],
            }
            if requested_language in fallback_by_lang:
                voices = fallback_by_lang[requested_language]
            else:
                voices = [{"id": "default", "label": "Predeterminada"}]
    except Exception as e:
        # Fallback robusto en caso de error interno
        sys.stderr.write(f"[api_voices] error: {e}\n")
        voices = [{"id": "default", "label": "Predeterminada"}]
    return jsonify({"voices": voices})


@app.route("/api/status", methods=["GET"])
def api_status():
    model_str = args.model_name or ""
    multilingual_flag = use_multi_language or ("xtts" in model_str or "multilingual" in model_str)
    return jsonify({
        "ready": synthesizer is not None,
        "multilingual": multilingual_flag,
        "multi_speaker": use_multi_speaker,
        "training": {
            "running": training_state["running"],
        }
    })


# ---- Swagger / OpenAPI (debe estar definido antes de app.run) ----
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    # Construir OpenAPI dinámico basado en los endpoints reales
    port = args.port if args.port else 5002
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Coqui TTS Server API",
            "version": "1.0.0",
            "description": "API para síntesis de voz, compatibilidad MaryTTS y entrenamiento.",
        },
        "servers": [
            {"url": f"http://127.0.0.1:{port}"},
            {"url": f"http://localhost:{port}"},
            {"url": "http://127.0.0.1:8001"},
        ],
        "paths": {
            "/api/status": {"get": {"summary": "Estado del servidor", "responses": {"200": {"description": "OK"}}}},
            "/api/languages": {"get": {"summary": "Lista de idiomas", "responses": {"200": {"description": "OK"}}}},
            "/api/voices": {"get": {"summary": "Lista de voces por idioma", "parameters": [{"name": "language", "in": "query", "schema": {"type": "string"}}], "responses": {"200": {"description": "OK"}}}},
            "/api/tts": {"get": {"summary": "Genera audio a partir de texto", "parameters": [
                {"name": "text", "in": "query", "schema": {"type": "string"}, "required": True},
                {"name": "speaker_id", "in": "query", "schema": {"type": "string"}},
                {"name": "language_id", "in": "query", "schema": {"type": "string"}},
                {"name": "style_wav", "in": "query", "schema": {"type": "string"}},
                {"name": "speaker_wav", "in": "query", "schema": {"type": "string"}},
            ], "responses": {"200": {"description": "Audio WAV"}, "400": {"description": "Parámetros inválidos"}, "503": {"description": "Modelo no listo"}, "500": {"description": "Error interno"}}}},
            "/api/train/upload": {"post": {"summary": "Subir archivos de audio para entrenamiento", "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object"}}}}, "responses": {"200": {"description": "OK"}, "400": {"description": "Error de subida"}}}},
            "/api/train/start": {"post": {"summary": "Iniciar proceso de entrenamiento", "requestBody": {"required": False, "content": {"application/json": {"schema": {"type": "object"}}}}, "responses": {"200": {"description": "Iniciado"}, "409": {"description": "Ya en curso"}}}},
            "/api/train/status": {"get": {"summary": "Estado de entrenamiento", "responses": {"200": {"description": "OK"}}}},
            "/api/train/stop": {"post": {"summary": "Detener entrenamiento", "responses": {"200": {"description": "OK"}}}},
            "/locales": {"get": {"summary": "Locales MaryTTS", "responses": {"200": {"description": "OK"}}}},
            "/voices": {"get": {"summary": "Voces MaryTTS", "responses": {"200": {"description": "OK"}}}},
            "/process": {"get": {"summary": "Procesar texto MaryTTS (GET)", "parameters": [{"name": "INPUT_TEXT", "in": "query", "schema": {"type": "string"}}], "responses": {"200": {"description": "Audio WAV"}}}, "post": {"summary": "Procesar texto MaryTTS (POST)", "requestBody": {"required": True, "content": {"application/x-www-form-urlencoded": {"schema": {"type": "object"}}}}, "responses": {"200": {"description": "Audio WAV"}}}},
        },
    }
    return jsonify(spec)


@app.route("/docs", methods=["GET"])
def swagger_ui():
    html = """
    <!DOCTYPE html>
    <html lang=\"es\">
    <head>
        <meta charset=\"utf-8\" />
        <title>Coqui TTS API Docs</title>
        <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\" />
    </head>
    <body>
        <div id=\"swagger-ui\"></div>
        <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
        <script>
          window.onload = () => {
            SwaggerUIBundle({
              url: '/openapi.json',
              dom_id: '#swagger-ui',
              presets: [SwaggerUIBundle.presets.apis],
              layout: 'BaseLayout'
            });
          };
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


# ---- Upload y Entrenamiento de modelos ----
@app.route("/api/train/upload", methods=["POST"])
def train_upload():
    try:
        upload_dir = os.path.join("/workspace", "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        files = request.files
        saved = []
        for key in files:
            f = files[key]
            if not f.filename:
                continue
            dest = os.path.join(upload_dir, os.path.basename(f.filename))
            f.save(dest)
            saved.append(dest)
        if not saved:
            return jsonify({"error": "No se recibieron archivos"}), 400
        return jsonify({"saved": saved})
    except Exception as e:
        return jsonify({"error": f"Fallo al subir audio: {e}"}), 500


@app.route("/api/train/start", methods=["POST"])
def train_start():
    with train_lock:
        if training_state["running"]:
            return jsonify({"error": "Entrenamiento ya en curso"}), 409
        data = request.get_json(silent=True) or {}
        model_name = data.get("model_name", "tts_models/multilingual/multi-dataset/xtts_v2")
        epochs = int(data.get("epochs", 1))
        out_dir = os.path.join("/workspace", "output", "training")
        os.makedirs(out_dir, exist_ok=True)
        log_path = os.path.join(out_dir, "train.log")
        # Comando base de entrenamiento (genérico). Para XTTS fine-tuning se requiere config específica.
        cmd = [
            "python", "-m", "TTS.bin.train_tts",
            "--model_name", model_name,
            "--epochs", str(epochs),
            "--output_path", out_dir,
        ]
        try:
            log_file = open(log_path, "w", buffering=1)
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            training_state.update({
                "running": True,
                "process": proc,
                "log_path": log_path,
                "start_time": time.time(),
                "params": {"model_name": model_name, "epochs": epochs},
            })
            return jsonify({"started": True, "pid": proc.pid, "log_path": log_path})
        except Exception as e:
            return jsonify({"error": f"No se pudo iniciar entrenamiento: {e}"}), 500


@app.route("/api/train/status", methods=["GET"])
def train_status():
    proc = training_state.get("process")
    running = training_state.get("running")
    log_path = training_state.get("log_path")
    status = {"running": bool(running)}
    if proc and proc.poll() is not None:
        # proceso finalizado
        training_state["running"] = False
        status["exit_code"] = proc.returncode
    # últimos 50 líneas del log
    lines = []
    try:
        if log_path and os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.readlines()
                lines = content[-50:]
    except Exception:
        lines = []
    status["log_tail"] = [l.strip() for l in lines]
    status["params"] = training_state.get("params")
    return jsonify(status)


@app.route("/api/train/stop", methods=["POST"])
def train_stop():
    with train_lock:
        proc = training_state.get("process")
        if not training_state.get("running") or not proc:
            return jsonify({"stopped": False, "message": "No hay entrenamiento en curso"})
        try:
            proc.terminate()
            training_state["running"] = False
            return jsonify({"stopped": True})
        except Exception as e:
            return jsonify({"error": f"No se pudo detener: {e}"}), 500


# Basic MaryTTS compatibility layer


@app.route("/locales", methods=["GET"])
def mary_tts_api_locales():
    """MaryTTS-compatible /locales endpoint"""
    # NOTE: We currently assume there is only one model active at the same time
    if args.model_name is not None:
        model_details = args.model_name.split("/")
    else:
        model_details = ["", "en", "", "default"]
    return render_template_string("{{ locale }}\n", locale=model_details[1])


@app.route("/voices", methods=["GET"])
def mary_tts_api_voices():
    """MaryTTS-compatible /voices endpoint"""
    # NOTE: We currently assume there is only one model active at the same time
    if args.model_name is not None:
        model_details = args.model_name.split("/")
    else:
        model_details = ["", "en", "", "default"]
    return render_template_string(
        "{{ name }} {{ locale }} {{ gender }}\n", name=model_details[3], locale=model_details[1], gender="u"
    )


@app.route("/process", methods=["GET", "POST"])
def mary_tts_api_process():
    """MaryTTS-compatible /process endpoint"""
    with lock:
        if request.method == "POST":
            data = parse_qs(request.get_data(as_text=True))
            # NOTE: we ignore param. LOCALE and VOICE for now since we have only one active model
            text = data.get("INPUT_TEXT", [""])[0]
        else:
            text = request.args.get("INPUT_TEXT", "")
        print(f" > Model input: {text}")
        wavs = synthesizer.tts(text)
        out = io.BytesIO()
        synthesizer.save_wav(wavs, out)
    return send_file(out, mimetype="audio/wav")



def main():
    # Bind explicitly to IPv4 to avoid connection resets on some hosts
    app.run(debug=args.debug, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
