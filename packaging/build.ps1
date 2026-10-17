param([string]$Python = 'python', [string]$Iscc = '')
$ErrorActionPreference = 'Stop'
$releaseRoot = Split-Path -Parent $PSScriptRoot
Push-Location $releaseRoot
try {
    New-Item -ItemType Directory -Path build -Force | Out-Null
    & "$env:WINDIR/Microsoft.NET/Framework64/v4.0.30319/csc.exe" /nologo /target:winexe /platform:anycpu /reference:System.Windows.Forms.dll /win32icon:app\assets\app_icon.ico /out:build\Uninstall.exe packaging\Uninstall.cs
    if ($LASTEXITCODE -ne 0) { throw 'Uninstall launcher compilation failed' }
    & "$env:WINDIR/Microsoft.NET/Framework64/v4.0.30319/csc.exe" /nologo /target:winexe /platform:anycpu /reference:System.Windows.Forms.dll /win32icon:app\assets\app_icon.ico /out:build\Update.exe packaging\Update.cs
    if ($LASTEXITCODE -ne 0) { throw 'Update helper compilation failed' }
    & $Python -m PyInstaller --noconfirm packaging/ScreenTranslator.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    if (-not $Iscc) {
        $compilerCandidates = @(
            (Join-Path $releaseRoot '.build-tools/InnoSetup/ISCC.exe'),
            "${env:ProgramFiles(x86)}/Inno Setup 6/ISCC.exe",
            "$env:LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe",
            "$env:LOCALAPPDATA/Programs/Inno Setup 7/ISCC.exe"
        )
        $Iscc = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $Iscc) { throw 'Install Inno Setup or pass -Iscc with the full path to ISCC.exe' }
    }
    $releaseVersion = & $Python -c 'from app.version import APP_VERSION; print(APP_VERSION)'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read app version' }
    & $Iscc "/DAppVersion=$releaseVersion" packaging/installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
    Copy-Item -LiteralPath build/Uninstall.exe -Destination release/Uninstall.exe -Force
    if (Test-Path -LiteralPath release/Uninstall.bat) { Remove-Item -LiteralPath release/Uninstall.bat }
    Get-FileHash -Algorithm SHA256 -LiteralPath "release/AI-Screen-Translator-$releaseVersion-Setup.exe", 'release/Uninstall.exe' |
        Format-List | Out-File -Encoding utf8 "release/SHA256.txt"
} finally {
    Pop-Location
}
