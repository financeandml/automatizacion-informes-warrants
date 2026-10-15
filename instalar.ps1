# Instalación en Windows (C3): ejecútalo en la carpeta del repositorio descargado de GitHub.
#   PowerShell:  powershell -ExecutionPolicy Bypass -File instalar.ps1
# Crea el entorno de Python FUERA de OneDrive, instala todo, prepara el PDF (WeasyPrint autónomo si no hay GTK)
# y deja abrir.bat para arrancar la interfaz en http://localhost:8501.
param([string]$Entorno = "$env:LOCALAPPDATA\informes-warrants\venv")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $crear = @("py", "-3", "-m", "venv", $Entorno) } else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { Write-Host "Instala Python 3.11 o superior desde https://www.python.org/downloads/ (marca 'Add to PATH')."; exit 1 }
    $crear = @("python", "-m", "venv", $Entorno)
}
if (-not (Test-Path "$Entorno\Scripts\python.exe")) {
    Write-Host "1/4 Creando el entorno en $Entorno"
    & $crear[0] $crear[1..($crear.Length - 1)]
}
$py = "$Entorno\Scripts\python.exe"
Write-Host "2/4 Instalando dependencias (unos minutos la primera vez)"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -e ".[pdf,ui,dev]" --quiet

Write-Host "3/4 Comprobando el PDF"
$gtk = & $py -c "import os, sys; os.add_dll_directory(r'C:\msys64\mingw64\bin') if os.path.isdir(r'C:\msys64\mingw64\bin') else None; import weasyprint; print('ok')" 2>$null
if ($gtk -ne "ok") {
    $destino = "$env:LOCALAPPDATA\informes-warrants\weasyprint"
    if (-not (Test-Path "$destino\weasyprint.exe")) {
        $version = & $py -c "import importlib.metadata as m; print(m.version('weasyprint'))"
        Write-Host "    Sin GTK: descargando WeasyPrint $version autónomo (GitHub oficial de Kozea)"
        New-Item -ItemType Directory -Force $destino | Out-Null
        $zip = "$destino\weasyprint.zip"
        Invoke-WebRequest "https://github.com/Kozea/WeasyPrint/releases/download/v$version/weasyprint-windows-onefile.zip" -OutFile $zip
        Expand-Archive $zip -DestinationPath $destino -Force
        Remove-Item $zip
        $exe = Get-ChildItem $destino -Recurse -Filter weasyprint.exe | Select-Object -First 1
        if ($exe -and $exe.DirectoryName -ne $destino) { Move-Item $exe.FullName "$destino\weasyprint.exe" -Force }
    }
}

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "    Creado .env (la interfaz te pedirá tu identificación de la SEC)" }
Set-Content -Path "abrir.bat" -Encoding ascii -Value "@echo off`r`n`"$py`" -m informes_warrants.cli interfaz"
Write-Host "4/4 Diagnóstico"
& $py -m informes_warrants.cli diagnostico
Write-Host "`nListo. Para abrir la interfaz: doble clic en abrir.bat (o: $py -m informes_warrants.cli interfaz)"
