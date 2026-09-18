"""Fix v2: redibujado de historial + comando /history."""
import ast
import pathlib

APP = pathlib.Path(r"D:\Trabajo\OvandoCode\src\ovandocode\tui\app.py")
lines = APP.read_text(encoding="utf-8").split("\n")

# Detectar qué falta
has_call = any("_redraw_history()" in l for l in lines)
has_method = any("def _redraw_history" in l for l in lines)
has_command = any('cmd == "history"' in l for l in lines)

print(f"Llamada en on_mount: {has_call}")
print(f"Metodo definido: {has_method}")
print(f"Comando /history: {has_command}")

# Si todo existe, salir
if has_call and has_method and has_command:
    print("[skip] Todo ya implementado")
    raise SystemExit(0)

# === Insertar metodo _redraw_history antes de _update_status ===
if not has_method:
    method_lines = [
        '    def _redraw_history(self) -> None:',
        '        """Redibuja el historial de la sesion en el chat."""',
        '        if not self.session or not self.session.messages:',
        '            return',
        '',
        '        log = self._log()',
        '        log.write("[dim]--- historial de la sesion reanudada ---[/]")',
        '        log.write("")',
        '',
        '        for msg in self.session.messages:',
        '            role = msg.role',
        '            content = msg.content or ""',
        '',
        '            if role == "system":',
        '                continue',
        '',
        '            if role == "user":',
        '                self._write_log(f"[bold green]Tu:[/] {content}")',
        '                self._write_log("")',
        '',
        '            elif role == "assistant":',
        '                if msg.tool_calls:',
        '                    for tc in msg.tool_calls:',
        '                        preview = str(tc.arguments)',
        '                        if len(preview) > 100:',
        '                            preview = preview[:100] + "..."',
        '                        self._write_log(f"[dim]  >> {tc.name} {preview}[/]")',
        '                if content.strip():',
        '                    self._write_log(f"[bold cyan]Agent:[/] {content}")',
        '                    self._write_log("")',
        '',
        '            elif role == "tool":',
        '                preview = content.replace("\\n", " ")',
        '                if len(preview) > 200:',
        '                    preview = preview[:200] + "..."',
        '                name = msg.name or "tool"',
        '                self._write_log(f"[dim]  << {name}: {preview}[/]")',
        '',
        '        log.write("")',
        '        log.write("[dim]--- fin del historial ---[/]")',
        '        log.write("")',
        '',
    ]
    for i, line in enumerate(lines):
        if "    def _update_status(self) -> None:" in line:
            lines = lines[:i] + method_lines + lines[i:]
            print("[OK] metodo _redraw_history insertado")
            break

# === Añadir llamada en on_mount ===
if not has_call:
    for i, line in enumerate(lines):
        if "await self.agent.__aenter__()" in line:
            # Insertar después de esta línea
            insert = [
                '',
                '        # Si la sesion fue reanudada, redibujar historial',
                '        if self.session.messages:',
                '            self._redraw_history()',
            ]
            lines = lines[:i+1] + insert + lines[i+1:]
            print("[OK] llamada en on_mount agregada")
            break

# === Añadir comando /history ===
if not has_command:
    for i, line in enumerate(lines):
        if 'elif cmd == "skills":' in line:
            insert = [
                '        elif cmd == "history":',
                '            self._redraw_history()',
            ]
            lines = lines[:i] + insert + lines[i:]
            print("[OK] comando /history agregado")
            break

# === Actualizar HELP_TEXT ===
new_txt = "\n".join(lines)
if "/history" not in new_txt.split("HELP_TEXT")[1].split('"""')[0] if "HELP_TEXT" in new_txt else True:
    for i, line in enumerate(lines):
        if "/session           Info de la sesion actual" in line:
            lines.insert(i + 1, "  /history           Redibuja el historial en el chat")
            print("[OK] HELP_TEXT actualizado")
            break

new_txt = "\n".join(lines)

# Validar sintaxis
try:
    ast.parse(new_txt)
    print("[OK] sintaxis valida")
except SyntaxError as e:
    print(f"[ERR] sintaxis rota linea {e.lineno}: {e.msg}")
    raise SystemExit(1)

APP.write_text(new_txt, encoding="utf-8", newline="\n")
print(f"[OK] {APP} guardado")

# Verificar
final = APP.read_text(encoding="utf-8")
print("")
print("=== Verificacion final ===")
for needle, label in [
    ("_redraw_history()", "llamada en on_mount"),
    ("def _redraw_history", "metodo definido"),
    ('cmd == "history"', "comando /history"),
    ("/history", "en HELP_TEXT"),
]:
    mark = "[OK]" if needle in final else "[!!]"
    print(f"  {mark} {label}")