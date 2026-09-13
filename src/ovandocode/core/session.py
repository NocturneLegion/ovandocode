"""Sesiones persistentes en formato JSONL (una linea por mensaje)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ovandocode.core.messages import from_dict, to_dict
from ovandocode.providers.types import Message


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:6]}"


@dataclass
class Session:
    """Sesion de conversacion persistida en disco."""
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    model: str = ""
    provider: str = ""
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    path: Path | None = None

    # ---------------- historial ----------------
    def append(self, msg: Message) -> None:
        self.messages.append(msg)
        self.updated_at = _now_iso()
        self._persist_append(msg)

    def extend(self, msgs: list[Message]) -> None:
        for m in msgs:
            self.append(m)

    def replace_history(self, msgs: list[Message]) -> None:
        """Reemplaza el historial completo (usado por compactacion)."""
        self.messages = list(msgs)
        self.updated_at = _now_iso()
        self._persist_full()

    def last_user_text(self) -> str:
        for m in reversed(self.messages):
            if m.role == "user":
                return m.content
        return ""

    def clear(self) -> None:
        self.messages.clear()
        self.updated_at = _now_iso()
        self._persist_full()

    # ---------------- persistencia ----------------
    def _persist_append(self, msg: Message) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_dict(msg), ensure_ascii=False) + "\n")
        self._write_meta()

    def _persist_full(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for m in self.messages:
                f.write(json.dumps(to_dict(m), ensure_ascii=False) + "\n")
        self._write_meta()

    def _write_meta(self) -> None:
        if self.path is None:
            return
        meta_path = self.path.with_suffix(".meta.json")
        meta = {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provider": self.provider,
            "model": self.model,
            "message_count": len(self.messages),
            "metadata": self.metadata,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------- IO publico ----------------

class SessionStore:
    """Gestiona el directorio de sesiones."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def new(self, provider: str = "", model: str = "") -> Session:
        s = Session(provider=provider, model=model)
        s.path = self.root / f"{s.id}.jsonl"
        s._write_meta()
        return s

    def load(self, session_id: str) -> Session:
        path = self.root / f"{session_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Sesion no encontrada: {session_id}")

        meta_path = path.with_suffix(".meta.json")
        meta: dict = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}

        msgs: list[Message] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msgs.append(from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError):
                continue

        s = Session(
            id=meta.get("id", session_id),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", ""),
            provider=meta.get("provider", ""),
            model=meta.get("model", ""),
            messages=msgs,
            metadata=meta.get("metadata", {}),
            path=path,
        )
        return s

    def list_sessions(self) -> list[dict]:
        """Lista metadatos de todas las sesiones (mas reciente primero)."""
        out: list[dict] = []
        for meta_path in self.root.glob("*.meta.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                out.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        out.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
        return out

    def delete(self, session_id: str) -> bool:
        p = self.root / f"{session_id}.jsonl"
        m = self.root / f"{session_id}.meta.json"
        deleted = False
        if p.exists():
            p.unlink()
            deleted = True
        if m.exists():
            m.unlink()
        return deleted