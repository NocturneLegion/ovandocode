"""Añadir redibujado del historial al reanudar sesión + comando /history."""
import ast
import pathlib

APP = pathlib.Path(r"D:\Trabajo\OvandoCode\src\ovandocode\tui\app.py")
txt = APP.read_text(encoding="utf-8")

# ============================================================
# 1. Agregar redibujado al final de on_mount
# ============================================================
old_on_mount_end = '''        await self.agent.__aenter__()
        self._update_status()
        self.query_one("#input", Input).focus()'''

new_on_mount_end = '''        await self.agent.__aenter__()

        # Si la sesion ya tiene mensajes previos (fue reanudada), redibujar
        if self.session.messages:
            self._redraw_history()

        self._update_status()
        self.query_one("#input", Input).focus()'''

if "_redraw_history" in txt:
    print("[skip] _redraw_history ya está integrado")
else:
    if old_on_mount_end in txt:
        txt = txt.replace(old_on_mount_end, new_on_mount_end, 1)
        print("[OK] on_mount: llamada a _redraw_history")
    else:
        print("[WARN] no se encontró el final de on_mount")


# ============================================================
# 2. Agregar el método _redraw_history
# ============================================================
anchor = "    def _update_status(self) -> None:"

redraw_method = '''    def _redraw_history(self) -> None:
        """Redibuja el historial de la sesion en el chat."""
        if not self.session or not self.session.messages:
            return

        log = self._log()
        log.write("[dim]--- historial de la sesion reanudada ---[/]")
        log.write("")

        for msg in self.session.messages:
            role = msg.role
            content = msg.content or ""

            if role == "system":
                # No mostrar el system prompt, es muy largo
                continue

            if role == "user":
                self._write_log(f"[bold green]Tu:[/] {content}")
                self._write_log("")

            elif role == "assistant":
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        preview = str(tc.arguments)
                        if len(preview) > 100:
                            preview = preview[:100] + "..."
                        self._write_log(f"[dim]  >> {tc.name} {preview}[/]")
                if content.strip():
                    self._write_log(f"[bold cyan]Agent:[/] {content}")
                    self._write_log("")

            elif role == "tool":
                preview = content.replace("\\n", " ")
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                name = msg.name or "tool"
                self._write_log(f"[dim]  << {name}: {preview}[/]")

        log.write("")
        log.write("[dim]--- fin del historial ---[/]")
        log.write("")

    def _update_status(self) -> None:'''

if "_redraw_history" in txt and "def _redraw_history" in txt:
    print("[skip] método _redraw_history ya existe")
else:
    if anchor in txt:
        txt = txt.replace(anchor, redraw_method, 1)
        print("[OK] método _redraw_history agregado")
    else:
        print("[WARN] no se encontró _update_status")


# ============================================================
# 3. Agregar comando /history al dispatcher
# ============================================================
old_branch = '''        elif cmd == "session":
            if self.session:
                self._write_log(
                    f"[bold]Sesion actual[/]\\n"
                    f"  id:       {self.session.id}\\n"
                    f"  provider: {self.session.provider}\\n"
                    f"  model:    {self.session.model}\\n"
                    f"  mensajes: {len(self.session.messages)}"
                )'''

new_branch = '''        elif cmd == "session":
            if self.session:
                self._write_log(
                    f"[bold]Sesion actual[/]\\n"
                    f"  id:       {self.session.id}\\n"
                    f"  provider: {self.session.provider}\\n"
                    f"  model:    {self.session.model}\\n"
                    f"  mensajes: {len(self.session.messages)}"
                )
        elif cmd == "history":
            self._redraw_history()'''

if 'cmd == "history"' in txt:
    print("[skip] comando /history ya existe")
else:
    if old_branch in txt:
        txt = txt.replace(old_branch, new_branch, 1)
        print("[OK] comando /history agregado")
    else:
        print("[WARN] no se encontró el bloque de /session")


# ============================================================
# 4. Actualizar HELP_TEXT
# ============================================================
if "/history" not in txt.split("HELP_TEXT")[1].split('"""')[1] if len(txt.split("HELP_TEXT")) > 1 else True:
    old_help = "  /session           Info de la sesion actual"
    new_help = "  /session           Info de la sesion actual\n  /history           Redibuja el historial en el chat"
    if old_help in txt:
        txt = txt.replace(old_help, new_help, 1)
        print("[OK] HELP_TEXT actualizado")


# ============================================================
# 5. Validar y guardar
# ============================================================
try:
    ast.parse(txt)
    print("[OK] sintaxis valida")
except SyntaxError as e:
    print(f"[ERR] sintaxis rota linea {e.lineno}: {e.msg}")
    raise SystemExit(1)

APP.write_text(txt, encoding="utf-8", newline="\n")
print(f"[OK] {APP} guardado")

# ============================================================
# 6. Verificación
# ============================================================
print("")
print("=== Verificacion ===")
final = APP.read_text(encoding="utf-8")
for needle, label in [
    ("_redraw_history()", "llamada en on_mount"),
    ("def _redraw_history", "método definido"),
    ('cmd == "history"', "comando /history en dispatcher"),
    ("/history", "documentado en HELP_TEXT"),
]:
    mark = "[OK]" if needle in final else "[!!]"
    print(f"  {mark} {label}")
'''

# Necesito volver a ejecutar la lógica en orden correcto
# El archivo anterior tiene un bug: el último bloque está fuera del if
# Voy a reescribir todo el script limpio
correct_script = '''"""Anadir redibujado del historial al reanudar sesion + comando /history."""
import ast
import pathlib

APP = pathlib.Path(r"D:\\Trabajo\\OvandoCode\\src\\ovandocode\\tui\\app.py")
txt = APP.read_text(encoding="utf-8")

changes = 0

# ============================================================
# 1. Llamada a _redraw_history en on_mount
# ============================================================
old_block = "        await self.agent.__aenter__()\\n        self._update_status()\\n        self.query_one(\\"#input\\", Input).focus()"
new_block = "        await self.agent.__aenter__()\\n\\n        # Si la sesion ya tiene mensajes previos (reanudada), redibujar\\n        if self.session.messages:\\n            self._redraw_history()\\n\\n        self._update_status()\\n        self.query_one(\\"#input\\", Input).focus()"

if "self._redraw_history()\\n" in txt and "if self.session.messages:" in txt:
    print("[skip] llamada ya existe")
elif old_block in txt:
    txt = txt.replace(old_block, new_block, 1)
    changes += 1
    print("[OK] llamada en on_mount")
else:
    print("[WARN] no se encontro el bloque de on_mount")


# ============================================================
# 2. Metodo _redraw_history
# ============================================================
anchor = "    def _update_status(self) -> None:"

method = (
    "    def _redraw_history(self) -> None:\\n"
    "        \\"\\"\\"Redibuja el historial de la sesion en el chat.\\"\\"\\"\\n"
    "        if not self.session or not self.session.messages:\\n"
    "            return\\n"
    "\\n"
    "        log = self._log()\\n"
    "        log.write(\\"[dim]--- historial de la sesion reanudada ---[/]\\")\\n"
    "        log.write(\\"\\")\\n"
    "\\n"
    "        for msg in self.session.messages:\\n"
    "            role = msg.role\\n"
    "            content = msg.content or \\"\\"\\n"
    "\\n"
    "            if role == \\"system\\":\\n"
    "                continue\\n"
    "\\n"
    "            if role == \\"user\\":\\n"
    "                self._write_log(f\\"[bold green]Tu:[/] {content}\\")\\n"
    "                self._write_log(\\"\\")\\n"
    "\\n"
    "            elif role == \\"assistant\\":\\n"
    "                if msg.tool_calls:\\n"
    "                    for tc in msg.tool_calls:\\n"
    "                        preview = str(tc.arguments)\\n"
    "                        if len(preview) > 100:\\n"
    "                            preview = preview[:100] + \\"...\\"\\n"
    "                        self._write_log(f\\"[dim]  >> {tc.name} {preview}[/]\\")\\n"
    "                if content.strip():\\n"
    "                    self._write_log(f\\"[bold cyan]Agent:[/] {content}\\")\\n"
    "                    self._write_log(\\"\\")\\n"
    "\\n"
    "            elif role == \\"tool\\":\\n"
    "                preview = content.replace(\\"\\\\n\\", \\" \\")\\n"
    "                if len(preview) > 200:\\n"
    "                    preview = preview[:200] + \\"...\\"\\n"
    "                name = msg.name or \\"tool\\"\\n"
    "                self._write_log(f\\"[dim]  << {name}: {preview}[/]\\")\\n"
    "\\n"
    "        log.write(\\"\\")\\n"
    "        log.write(\\"[dim]--- fin del historial ---[/]\\")\\n"
    "        log.write(\\"\\")\\n"
    "\\n"
    "    def _update_status(self) -> None:"
)

if "def _redraw_history" in txt:
    print("[skip] metodo ya existe")
elif anchor in txt:
    txt = txt.replace(anchor, method, 1)
    changes += 1
    print("[OK] metodo _redraw_history")
else:
    print("[WARN] no se encontro _update_status")


# ============================================================
# 3. Comando /history en dispatcher
# ============================================================
old_session = (
    "        elif cmd == \\"session\\":\\n"
    "            if self.session:\\n"
    "                self._write_log(\\n"
    "                    f\\"[bold]Sesion actual[/]\\\\n\\"\\n"
    "                    f\\"  id:       {self.session.id}\\\\n\\"\\n"
    "                    f\\"  provider: {self.session.provider}\\\\n\\"\\n"
    "                    f\\"  model:    {self.session.model}\\\\n\\"\\n"
    "                    f\\"  mensajes: {len(self.session.messages)}\\"\\n"
    "                )"
)

new_session = old_session + (
    "\\n"
    "        elif cmd == \\"history\\":\\n"
    "            self._redraw_history()"
)

if 'cmd == "history"' in txt:
    print("[skip] comando /history ya existe")
elif old_session in txt:
    txt = txt.replace(old_session, new_session, 1)
    changes += 1
    print("[OK] comando /history")
else:
    print("[WARN] no se encontro el bloque de /session")


# ============================================================
# 4. HELP_TEXT
# ============================================================
if "/history" not in txt:
    old_help = "  /session           Info de la sesion actual"
    new_help = old_help + "\\n  /history           Redibuja el historial en el chat"
    if old_help in txt:
        txt = txt.replace(old_help, new_help, 1)
        changes += 1
        print("[OK] HELP_TEXT actualizado")
    else:
        print("[WARN] no se encontro /session en HELP_TEXT")
else:
    print("[skip] HELP_TEXT ya tiene /history")


# ============================================================
# 5. Validar y guardar
# ============================================================
try:
    ast.parse(txt)
    print("[OK] sintaxis valida")
except SyntaxError as e:
    print(f"[ERR] sintaxis rota linea {e.lineno}: {e.msg}")
    raise SystemExit(1)

APP.write_text(txt, encoding="utf-8", newline="\\n")
print(f"[OK] {APP} guardado ({changes} cambios)")
'''

# Nota: el correct_script no se usa, es solo una referencia mental.
# Vamos con el script simplificado de abajo
print("Usar el script de abajo")