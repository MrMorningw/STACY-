"""Strict, deterministic Android action parser.

Only clear imperative phrases are translated to native actions. The model is
not allowed to invent package names or invoke arbitrary shell commands.
"""
import re
import unicodedata


APP_ALIASES = {
    "whatsapp": ("WhatsApp", "com.whatsapp"),
    "youtube": ("YouTube", "com.google.android.youtube"),
    "chrome": ("Chrome", "com.android.chrome"),
    "gmail": ("Gmail", "com.google.android.gm"),
    "spotify": ("Spotify", "com.spotify.music"),
    "maps": ("Google Maps", "com.google.android.apps.maps"),
    "google maps": ("Google Maps", "com.google.android.apps.maps"),
}


def _fold(text):
    text = unicodedata.normalize("NFD", (text or "").strip().lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _normalize(text):
    text = _fold(text)
    text = re.sub(r"[?!.,;]+", " ", text)
    return " ".join(text.split()).rstrip(": ")


def detectar_acao_android(mensagem):
    """Return a typed action only for explicit, allowlisted user commands."""
    texto = _normalize(mensagem)
    if texto in {
        "abra as configuracoes",
        "abrir configuracoes",
        "abra as configuracoes do android",
        "abrir configuracoes do android",
        "abra configuracoes do sistema",
        "abrir configuracoes do sistema",
    }:
        return {"acao": "abrir_configuracoes"}

    if texto in {
        "abra o calendario",
        "abrir o calendario",
        "abra calendario",
        "abrir calendario",
        "abra minha agenda",
        "abrir minha agenda",
    }:
        return {"acao": "abrir_calendario"}

    if texto in {
        "selecione um arquivo",
        "selecionar arquivo",
        "escolha um arquivo",
        "escolher arquivo",
        "anexar arquivo",
        "anexar um arquivo",
    }:
        return {"acao": "selecionar_arquivo", "mime_type": "*/*"}

    folded_original = _fold(mensagem)
    share_match = re.fullmatch(
        r"(?:compartilhe|compartilhar|compartilhe o texto)\s*:\s*(.+)",
        folded_original,
        flags=re.DOTALL,
    )
    if share_match:
        original_content = mensagem.split(":", 1)[1].strip()
        if original_content:
            return {"acao": "compartilhar_texto", "texto": original_content}

    match = re.fullmatch(
        r"(?:por favor )?(?:abra|abrir|abre|inicie|iniciar) "
        r"(?:(?:o|a) )?(?:aplicativo )?(.+)",
        texto,
    )
    if match:
        alias = match.group(1).strip()
        app = APP_ALIASES.get(alias)
        if app:
            return {
                "acao": "abrir_aplicativo",
                "nome": app[0],
                "pacote": app[1],
            }

    return None
