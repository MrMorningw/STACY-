import shutil
import subprocess


def disponivel():
    return shutil.which("termux-speech-to-text") is not None


def ouvir(timeout=60):
    comando = shutil.which("termux-speech-to-text")
    if not comando:
        raise RuntimeError("termux-speech-to-text não está instalado.")
    processo = subprocess.run(
        [comando],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if processo.returncode != 0:
        raise RuntimeError((processo.stderr or "falha no reconhecimento de voz").strip())
    texto = (processo.stdout or "").strip()
    if not texto:
        raise RuntimeError("nenhuma fala reconhecida.")
    return texto


def falar(texto, timeout=60):
    comando = shutil.which("termux-tts-speak")
    if not comando:
        return False
    processo = subprocess.run(
        [comando, texto],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return processo.returncode == 0
