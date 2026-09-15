# fix_theme.ps1 - Regenera theme.tcss sin errores

$File = "src\ovandocode\tui\theme.tcss"

$Content = @'
/* Tema Oscuro para OvandoCode */

Screen {
    background: $surface;
    color: $text;
}

#header {
    background: $primary-background;
    color: $text;
}

#footer {
    background: $boost;
    color: $text-muted;
}

#chat-history {
    background: $surface;
    color: $text;
}

#command-input {
    background: $boost;
    color: $text;
}

/* Modal de Credenciales */
#creds-modal, #creds-list-modal {
    align: center middle;
    width: 60;
    height: auto;
    max-height: 80%;
    background: $surface;
    border: thick $primary;
    padding: 1 2;
}

#creds-title, #list-title {
    text-align: center;
    text-style: bold;
    color: $text;
    margin-bottom: 1;
}

#provider-select, #api-key-input {
    width: 100%;
    margin-bottom: 1;
}

#creds-buttons, #list-buttons {
    align: center middle;
    margin-top: 1;
}

.provider-item-configured {
    background: #004400;
    color: #00ff00;
    padding: 0 1;
    margin: 1 0;
}

.provider-item-missing {
    background: #440000;
    color: #ff5555;
    padding: 0 1;
    margin: 1 0;
}

#list-hint {
    text-align: center;
    color: $text-muted;
    margin: 1 0;
}
'@

# Escribir el archivo sin BOM
[System.IO.File]::WriteAllText((Resolve-Path $File).Path, $Content, [System.Text.UTF8Encoding]::new($false))

Write-Host "Archivo theme.tcss regenerado correctamente." -ForegroundColor Green
Write-Host "Iniciando OvandoCode..." -ForegroundColor Cyan