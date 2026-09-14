"""Politica de permisos para ejecucion de comandos y tools."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Decision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


Mode = Literal["ask", "allowlist", "yolo"]


@dataclass
class PermissionVerdict:
    decision: Decision
    reason: str = ""


# Patrones de comandos considerados "peligrosos" (nunca auto-permitir)
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\bformat\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{",            # fork bomb
    r"\bRemove-Item\b.*-Recurse.*-Force",
    r"\brmdir\s+/s",
    r"\bdel\s+/f\s+/s\s+/q",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bdiskpart\b",
    r"\bbcdedit\b",
    r"\breg\s+delete\b",
    r"\bSet-ExecutionPolicy\s+Unrestricted",
    r"\bcurl\b.*\|\s*(bash|sh|powershell|pwsh|iex)",
    r"\biwr\b.*\|\s*iex",
    r"\bInvoke-Expression\b",
    r"\bInvoke-WebRequest\b.*\|\s*Invoke-Expression",
]

# Comandos seguros auto-permitidos (solo lectura/informativos)
DEFAULT_ALLOWLIST = [
    # PowerShell / Windows
    r"^Get-\w+",
    r"^Test-\w+",
    r"^Select-\w+",
    r"^Where-\w+",
    r"^Measure-\w+",
    r"^Resolve-Path\b",
    r"^Get-ChildItem\b",
    r"^Get-Content\b",
    r"^Get-Location\b",
    r"^Get-Date\b",
    r"^Get-Host\b",
    r"^Write-Output\b",
    r"^Write-Host\b",
    r"^echo\b",
    r"^dir\b",
    r"^type\b",
    r"^pwd\b",
    r"^cd\b",
    r"^whoami\b",
    r"^hostname\b",
    # POSIX (bash)
    r"^ls\b",
    r"^cat\b",
    r"^head\b",
    r"^tail\b",
    r"^wc\b",
    r"^grep\b",
    r"^rg\b",
    r"^find\b",
    r"^which\b",
    r"^whereis\b",
    r"^echo\b",
    r"^pwd\b",
    r"^env\b",
    r"^printenv\b",
    r"^uname\b",
    r"^whoami\b",
    # Git read-only
    r"^git\s+status\b",
    r"^git\s+log\b",
    r"^git\s+diff\b",
    r"^git\s+show\b",
    r"^git\s+branch\b(?!\s+-[dD])",
    r"^git\s+remote\b(?!\s+(add|remove|rm))",
    r"^git\s+rev-parse\b",
    # Python read-only
    r"^python\b.*--version",
    r"^python\b.*-V\b",
    r"^pip\s+list\b",
    r"^uv\s+pip\s+list\b",
]


@dataclass
class PermissionPolicy:
    """Decide si un comando puede ejecutarse.

    Modos:
      - ask:       siempre preguntar
      - allowlist: auto-permitir los que estan en allowlist, resto preguntar
      - yolo:      auto-permitir todo EXCEPTO patrones peligrosos (que igual preguntan)
    """
    mode: Mode = "allowlist"
    allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWLIST))
    denylist: list[str] = field(default_factory=lambda: list(DANGEROUS_PATTERNS))
    _allow_rx: list[re.Pattern] = field(default_factory=list, init=False)
    _deny_rx: list[re.Pattern] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._allow_rx = [re.compile(p, re.IGNORECASE) for p in self.allowlist]
        self._deny_rx = [re.compile(p, re.IGNORECASE) for p in self.denylist]

    def decide(self, command: str) -> PermissionVerdict:
        cmd = command.strip()
        if not cmd:
            return PermissionVerdict(Decision.DENY, "comando vacio")

        # 1) Denylist siempre gana -> preguntar (no denegar del todo para no ser molesto)
        for rx in self._deny_rx:
            if rx.search(cmd):
                return PermissionVerdict(Decision.ASK, f"patron peligroso: {rx.pattern}")

        # 2) Modo yolo -> permitir todo lo que no sea peligroso
        if self.mode == "yolo":
            return PermissionVerdict(Decision.ALLOW, "modo yolo")

        # 3) Modo ask -> siempre preguntar
        if self.mode == "ask":
            return PermissionVerdict(Decision.ASK, "modo ask")

        # 4) Modo allowlist
        for rx in self._allow_rx:
            if rx.search(cmd):
                return PermissionVerdict(Decision.ALLOW, f"allowlist: {rx.pattern}")

        return PermissionVerdict(Decision.ASK, "no esta en allowlist")

    def is_safe(self, command: str) -> bool:
        return self.decide(command).decision == Decision.ALLOW


def parse_command_tokens(command: str) -> list[str]:
    """Divide un comando en tokens (soporta comillas simples y dobles)."""
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()
