"""
Motor de geração de vídeo via FFmpeg.

Para cada foto do imóvel:
  1. Enquadra em formato vertical (1080x1920 - estilo Reels/Stories).
  2. Aplica efeito Ken Burns (zoom + pan lento) via filtro `zoompan`.
Entre as fotos:
  3. Aplica transição crossfade (`xfade`) suave.
Por cima do vídeo final:
  4. Mixa uma trilha ambiente 100% sintetizada (osciladores `sine` do
     próprio FFmpeg, sem dependência de arquivos de áudio externos),
     com timbre e andamento diferentes por estilo.

Três estilos são suportados: "classico", "moderno" e "suave", cada um
com sua própria curva de cor, velocidade de zoom, tipo de transição e
paleta de frequências da trilha sonora.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

logger = logging.getLogger("pipeline")

# ---- Parâmetros globais de renderização ----
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24  # zoompan processa 1 frame de swscale por frame de saida; fps menor = bem mais rapido
SECONDS_PER_PHOTO = 4.0
CROSSFADE_DURATION = 1.0
UPSCALE_FACTOR = 1.0  # sem supersampling extra antes do zoompan (era o maior custo de CPU)
FILTER_THREADS = "0"  # "0" = ffmpeg escolhe automaticamente (usa todos os nucleos disponiveis)


class PipelineError(RuntimeError):
    """Erro durante execução do FFmpeg."""


@dataclass(frozen=True)
class StyleConfig:
    key: str
    label: str
    zoom_max: float                # zoom máximo atingido ao final do Ken Burns
    eq_filter: str                 # filtros de imagem (cor/nitidez) do estilo
    transition: str                # nome da transição xfade
    music_freqs: list[float]       # frequências (Hz) da trilha ambiente sintetizada
    music_weights: list[float]     # peso de cada camada no mix
    music_tempo: float             # velocidade do tremolo/movimento da trilha


STYLES: dict[str, StyleConfig] = {
    "classico": StyleConfig(
        key="classico",
        label="Clássico",
        zoom_max=1.15,
        eq_filter="eq=saturation=0.92:contrast=1.06:brightness=0.02:gamma=1.02",
        transition="fade",
        music_freqs=[196.00, 246.94, 293.66],   # tríade de Sol maior (G-B-D)
        music_weights=[1.0, 0.75, 0.55],
        music_tempo=0.15,
    ),
    "moderno": StyleConfig(
        key="moderno",
        label="Moderno",
        zoom_max=1.28,
        eq_filter="eq=saturation=1.28:contrast=1.18:brightness=0.0",
        transition="wipeleft",
        music_freqs=[110.00, 164.81, 220.00, 277.18],  # A2, E3, A3, C#4
        music_weights=[1.0, 0.6, 0.5, 0.35],
        music_tempo=0.35,
    ),
    "suave": StyleConfig(
        key="suave",
        label="Suave",
        zoom_max=1.10,
        eq_filter="eq=saturation=1.0:contrast=0.95:brightness=0.03,gblur=sigma=0.25",
        transition="dissolve",
        music_freqs=[261.63, 329.63, 392.00],   # tríade de Dó maior (C-E-G)
        music_weights=[1.0, 0.65, 0.5],
        music_tempo=0.12,  # filtro `tremolo` do ffmpeg exige f >= 0.1
    ),
}

DEFAULT_STYLE = "classico"


def _run(args: list[str], step: str) -> None:
    cmd = [settings.FFMPEG_BINARY, "-y", "-hide_banner", "-loglevel", "error", *args]
    logger.info("ffmpeg[%s]: %s", step, " ".join(cmd))
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise PipelineError(f"Falha no FFmpeg durante '{step}': {result.stdout[-4000:]}")


def _pan_expressions(direction: int, frames: int) -> tuple[str, str]:
    """Retorna as expressões (x, y) do zoompan para uma das 4 direções de pan."""
    progress = f"(on/{max(frames - 1, 1)})"
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"
    left_to_right = f"(iw-iw/zoom)*{progress}"
    top_to_bottom = f"(ih-ih/zoom)*{progress}"

    variants = [
        (center_x, center_y),                 # 0: zoom centrado
        (left_to_right, center_y),             # 1: pan horizontal
        (center_x, top_to_bottom),             # 2: pan vertical
        (left_to_right, top_to_bottom),        # 3: pan diagonal
    ]
    return variants[direction % len(variants)]


def _render_ken_burns_clip(photo_path: Path, clip_path: Path, style: StyleConfig, index: int) -> None:
    """Renderiza uma foto em um clipe de vídeo com efeito Ken Burns + cor do estilo."""
    duration = SECONDS_PER_PHOTO
    frames = int(duration * FPS)
    zoom_step = (style.zoom_max - 1.0) / frames

    x_expr, y_expr = _pan_expressions(index, frames)
    supersample = (
        f"scale={int(VIDEO_WIDTH * UPSCALE_FACTOR)}:{int(VIDEO_HEIGHT * UPSCALE_FACTOR)},"
        if UPSCALE_FACTOR > 1.0
        else ""
    )

    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"{supersample}"
        f"zoompan=z='min(zoom+{zoom_step:.6f},{style.zoom_max})':"
        f"x='{x_expr}':y='{y_expr}':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
        f"{style.eq_filter},"
        "format=yuv420p"
    )

    args = [
        "-loop", "1",
        "-t", f"{duration}",
        "-i", str(photo_path),
        "-vf", vf,
        "-filter_threads", FILTER_THREADS,
        "-an",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "0",
        "-pix_fmt", "yuv420p",
        str(clip_path),
    ]
    _run(args, f"ken-burns-{index}")


def _generate_ambient_track(audio_path: Path, style: StyleConfig, duration: float) -> None:
    """Sintetiza uma trilha ambiente a partir de osciladores senoidais do FFmpeg."""
    duration = max(duration, 1.0)
    inputs: list[str] = []
    for freq in style.music_freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}:sample_rate=44100"]

    n = len(style.music_freqs)
    weights = " ".join(f"{w:.2f}" for w in style.music_weights)
    fade_out_start = max(duration - 3.0, 0.0)

    input_labels = "".join(f"[{i}:a]" for i in range(n))
    filter_complex = (
        f"{input_labels}"
        f"amix=inputs={n}:duration=longest:weights={weights},"
        f"tremolo=f={style.music_tempo}:d=0.3,"
        "lowpass=f=2800,"
        "aecho=0.6:0.5:60:0.3,"
        "volume=0.15,"
        f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out_start}:d=3"
        "[aout]"
    )

    args = [
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-ar", "44100",
        str(audio_path),
    ]
    _run(args, "ambient-track")


def _concat_with_crossfade(
    clip_paths: list[Path],
    audio_path: Path,
    output_path: Path,
    style: StyleConfig,
) -> None:
    """Concatena os clipes com transição xfade e mixa a trilha ambiente."""
    n = len(clip_paths)
    inputs: list[str] = []
    for clip in clip_paths:
        inputs += ["-i", str(clip)]
    audio_index = n
    inputs += ["-i", str(audio_path)]

    if n == 1:
        filter_complex = "[0:v]null[vout]"
    else:
        parts = []
        current_label = "0:v"
        cumulative_duration = SECONDS_PER_PHOTO
        for i in range(1, n):
            next_label = f"v{i:02d}"
            offset = cumulative_duration - CROSSFADE_DURATION
            parts.append(
                f"[{current_label}][{i}:v]xfade=transition={style.transition}:"
                f"duration={CROSSFADE_DURATION}:offset={offset:.3f}[{next_label}]"
            )
            cumulative_duration = offset + SECONDS_PER_PHOTO
            current_label = next_label
        final_label = current_label
        parts.append(f"[{final_label}]format=yuv420p[vout]")
        filter_complex = ";".join(parts)

    args = [
        *inputs,
        "-filter_complex", filter_complex,
        "-filter_complex_threads", FILTER_THREADS,
        "-map", "[vout]",
        "-map", f"{audio_index}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-threads", "0",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]
    _run(args, "concat-xfade")


def total_duration_seconds(num_photos: int) -> float:
    if num_photos <= 0:
        return 0.0
    return SECONDS_PER_PHOTO * num_photos - CROSSFADE_DURATION * max(num_photos - 1, 0)


def generate_video(photo_paths: list[Path], style_key: str, output_path: Path) -> Path:
    """Gera o vídeo final a partir das fotos, aplicando o estilo escolhido.

    Roda de forma síncrona/bloqueante — pensado para ser chamado a partir de
    uma tarefa em background (ver `main.py`).
    """
    if not photo_paths:
        raise PipelineError("Nenhuma foto fornecida para geração do vídeo.")

    style = STYLES.get(style_key, STYLES[DEFAULT_STYLE])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        tmp_dir = Path(tmp)
        clip_paths: list[Path] = []
        for i, photo in enumerate(photo_paths):
            clip_path = tmp_dir / f"clip_{i:03d}.mp4"
            _render_ken_burns_clip(photo, clip_path, style, i)
            clip_paths.append(clip_path)

        duration = total_duration_seconds(len(clip_paths))
        audio_path = tmp_dir / "ambient.wav"
        _generate_ambient_track(audio_path, style, duration)

        _concat_with_crossfade(clip_paths, audio_path, output_path, style)

    return output_path
