param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path,
  [string]$OutDir = (Join-Path $RepoRoot "dist\\GermanNewWords"),
  [string]$VenvDir = (Join-Path $RepoRoot "Tools\\.exe_venv"),
  [switch]$Clean
)

$ErrorActionPreference = "Stop"

Set-Location $RepoRoot

if ($Clean) {
  if (Test-Path -LiteralPath $OutDir) {
    Remove-Item -LiteralPath $OutDir -Recurse -Force
  }
  if (Test-Path -LiteralPath (Join-Path $RepoRoot "build")) {
    Remove-Item -LiteralPath (Join-Path $RepoRoot "build") -Recurse -Force
  }
  if (Test-Path -LiteralPath $VenvDir) {
    Remove-Item -LiteralPath $VenvDir -Recurse -Force
  }
}

Write-Host "[STEP] Build Windows exe (console) via PyInstaller"
Write-Host "[INFO] Output dir: $OutDir"

$toolsDir = Join-Path $RepoRoot "Tools"
Set-Location $toolsDir

if (-not (Test-Path -LiteralPath $VenvDir)) {
  Write-Host "[STEP] Create isolated venv for exe build: $VenvDir"
  py -m venv $VenvDir
}

$py = Join-Path $VenvDir "Scripts\\python.exe"

Write-Host "[STEP] Install minimal deps into venv"
& $py -m pip install -U pip
& $py -m pip install -e ".[dist]"

$exclude = @(
  "pytest",
  "numpy",
  "pandas",
  "scipy",
  "matplotlib",
  "sklearn",
  "tensorflow",
  "torch",
  "transformers",
  "IPython",
  "jedi",
  "parso"
)

$excludeArgs = @()
foreach ($m in $exclude) { $excludeArgs += @("--exclude-module", $m) }

Write-Host "[STEP] PyInstaller build (isolated site-packages)"
$env:PYTHONNOUSERSITE = "1"

& $py -m PyInstaller `
  --name GermanNewWords `
  --onefile `
  --console `
  --distpath $OutDir `
  --clean `
  $excludeArgs `
  (Join-Path $toolsDir "src\\gnw\\__main__.py")

Write-Host "[OK] Built: $OutDir\\GermanNewWords.exe"
