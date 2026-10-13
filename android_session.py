"""Private, atomic persistence for the Android-launched STACY CORE session.

Each Android message starts a short-lived Termux/Python process. This store
preserves only the serializable conversational state needed across those
processes; tasks, entities, and long-term memory keep their existing stores.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import time


SCHEMA_VERSION = 1
MAX_HISTORY = 12


def _directory():
    override = os.environ.get("STACY_STATE_DIR")
    return Path(override).expanduser() if override else Path.home() / ".stacy"


def _prepare_directory():
    directory = _directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    return directory


@contextmanager
def exclusive_session_lock():
    """Serialize requests so simultaneous Android taps cannot overwrite state."""
    directory = _prepare_directory()
    lock_path = directory / "session.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            os.chmod(lock_path, 0o600)
        except OSError:
            pass
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def load_api_key():
    """Read the Gemini key from the process environment or a private local file."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    directory = _prepare_directory()
    path = directory / "secrets.json"
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError("The private API-key file must not be a symbolic link.")

    try:
        os.chmod(path, 0o600)
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("The private API-key file could not be read.") from error

    if not isinstance(data, dict):
        raise ValueError("The private API-key file has an invalid format.")
    key = data.get("GEMINI_API_KEY", data.get("gemini_api_key", ""))
    if key is None:
        return None
    if not isinstance(key, str):
        raise ValueError("The Gemini API key must be a string.")
    return key.strip() or None


def restore_session(orchestrator):
    """Restore a validated session. Return a warning if the prior file is corrupt."""
    path = _directory() / "session.json"
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            state = json.load(file)
        if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported session schema")

        history = state.get("historico", [])
        pending_action = state.get("acao_pendente")
        last_decision = state.get("ultima_decisao")
        entity_context = state.get("entidade_contextual")
        conversation_state = state.get("conversa", {})

        if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
            raise ValueError("invalid orchestrator history")
        if pending_action is not None and not isinstance(pending_action, dict):
            raise ValueError("invalid pending action")
        if last_decision is not None and not isinstance(last_decision, dict):
            raise ValueError("invalid last decision")
        if entity_context is not None and not isinstance(entity_context, dict):
            raise ValueError("invalid entity context")
        if not isinstance(conversation_state, dict):
            raise ValueError("invalid conversation state")

        known_fields = vars(orchestrator.conversa)
        if not set(conversation_state).issubset(known_fields):
            raise ValueError("unknown conversation fields")
        if conversation_state.get("estado_operacional", "ocioso") not in orchestrator.conversa.ESTADOS_OPERACIONAIS:
            raise ValueError("invalid operational state")
        conversation_history = conversation_state.get("historico", [])
        if not isinstance(conversation_history, list) or any(
            not isinstance(item, dict) for item in conversation_history
        ):
            raise ValueError("invalid conversation history")

        orchestrator.historico = history[-MAX_HISTORY:]
        orchestrator.acao_pendente = pending_action
        orchestrator.ultima_decisao = last_decision
        orchestrator.entidade_contextual = entity_context
        for field, value in conversation_state.items():
            setattr(orchestrator.conversa, field, value)
        orchestrator.conversa.historico = conversation_history[-orchestrator.conversa.limite:]
        return None
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        # Do not silently reuse a potentially stale pending destructive action.
        backup = path.with_name(f"session.corrupt.{int(time.time())}.json")
        try:
            path.replace(backup)
        except OSError:
            pass
        return (
            "O estado anterior da conversa estava inválido; foi isolado para segurança. "
            "Esta sessão será retomada sem a ação pendente anterior."
        )


def persist_session(orchestrator):
    """Atomically save the bounded conversation state with owner-only permissions."""
    directory = _prepare_directory()
    path = directory / "session.json"
    temporary = directory / "session.json.tmp"
    state = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": time.time(),
        "historico": orchestrator.historico[-MAX_HISTORY:],
        "acao_pendente": orchestrator.acao_pendente,
        "ultima_decisao": orchestrator.ultima_decisao,
        "entidade_contextual": orchestrator.entidade_contextual,
        "conversa": vars(orchestrator.conversa),
    }
    serialized = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    with temporary.open("w", encoding="utf-8") as file:
        os.chmod(temporary, 0o600)
        file.write(serialized)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
