# Build native/core_map (requires CMake + a C compiler)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
cmake -S "$root\native\core_map" -B "$root\native\core_map\build"
cmake --build "$root\native\core_map\build" --config Release
Write-Host "OK: native/core_map/build"
