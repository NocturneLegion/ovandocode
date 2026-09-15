$filePath = "src\ovandocode\tui\app.py"
$content = Get-Content $filePath -Raw -Encoding UTF8

# Definimos el código Python a agregar como una cadena cruda
$codeToAdd = @"

    def on_mount(self) -> None:
        self.query_one("#command-input", Input).focus()

    async def handle_command(self, command: str) -> None:
        """Procesa comandos slash."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            self.notify("Comandos: /help, /clear, /credentials, /credentials config", severity="information")
        elif cmd == "clear":
            self.query_one("#chat-history", RichLog).clear()
            self.notify("Historial limpiado", severity="information")
        elif cmd == "credentials":
            from .widgets.credentials import CredentialsListScreen, CredentialsScreen
            if args.lower() == "config":
                self.push_screen(CredentialsScreen())
            else:
                self.push_screen(CredentialsListScreen())
        else:
            self.notify(f"Comando desconocido: {cmd}", severity="warning")
"@

# Verificamos si ya existe para no duplicar
if ($content -match "def handle_command") {
    Write-Host "El comando ya existe en el archivo." -ForegroundColor Yellow
} else {
    # Añadimos el código al final del archivo
    Set-Content -Path $filePath -Value ($content + $codeToAdd) -Encoding UTF8 -NoNewline
    Write-Host "Código insertado correctamente al final del archivo." -ForegroundColor Green
}