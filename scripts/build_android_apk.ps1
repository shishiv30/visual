# Build the Visual Pose Android debug APK and optionally install it over adb.
$ErrorActionPreference = "Stop"

function Find-JavaHome {
    if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
        return $env:JAVA_HOME
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "jdk-17")
    )
    $candidates += @(Get-ChildItem "C:\Program Files\Microsoft\jdk-17*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    $candidates += @(Get-ChildItem "C:\Program Files\Eclipse Adoptium\jdk-17*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    foreach ($dir in $candidates) {
        if ($dir -and (Test-Path (Join-Path $dir "bin\java.exe"))) {
            return $dir
        }
    }
    $javaCmd = Get-Command java -ErrorAction SilentlyContinue
    if ($javaCmd) {
        $homeDir = Split-Path (Split-Path $javaCmd.Source -Parent) -Parent
        if (Test-Path (Join-Path $homeDir "bin\java.exe")) {
            return $homeDir
        }
    }
    return $null
}

$javaHome = Find-JavaHome
if (-not $javaHome) {
    throw "JDK 17 not found. Install Microsoft OpenJDK 17 (or Temurin 17) and set JAVA_HOME."
}
$env:JAVA_HOME = $javaHome
$env:Path = "$(Join-Path $javaHome 'bin');" + $env:Path
Write-Host "JAVA_HOME=$javaHome"

$root = Split-Path -Parent $PSScriptRoot
$android = Join-Path $root "clients\android"
$apk = Join-Path $android "app\build\outputs\apk\debug\app-debug.apk"
$model = Join-Path $root "models\pose_landmarker_full.task"
$localProps = Join-Path $android "local.properties"

function Find-AndroidSdk {
    if ($env:ANDROID_HOME -and (Test-Path $env:ANDROID_HOME)) {
        return $env:ANDROID_HOME
    }
    if ($env:ANDROID_SDK_ROOT -and (Test-Path $env:ANDROID_SDK_ROOT)) {
        return $env:ANDROID_SDK_ROOT
    }
    $studio = Join-Path $env:LOCALAPPDATA "Android\Sdk"
    if (Test-Path $studio) {
        return $studio
    }
    if (Test-Path $localProps) {
        foreach ($line in Get-Content $localProps) {
            if ($line -match '^\s*sdk\.dir=(.+)$') {
                $dir = $Matches[1].Trim().Replace("\\", "\").Replace("/", "\")
                if (Test-Path $dir) {
                    return $dir
                }
            }
        }
    }
    return $null
}

$sdk = Find-AndroidSdk
if (-not $sdk) {
    throw @"
Android SDK not found. Install Android Studio (API 35 + NDK 28.1+) or the command-line tools, then set ANDROID_HOME or create clients\android\local.properties with:
sdk.dir=C:\\Users\\<you>\\AppData\\Local\\Android\\Sdk
"@
}

if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = $sdk
}
if (-not $env:ANDROID_SDK_ROOT) {
    $env:ANDROID_SDK_ROOT = $sdk
}

if (-not (Test-Path $localProps)) {
    $escaped = $sdk.Replace("\", "\\")
    Set-Content -Path $localProps -Value "sdk.dir=$escaped" -Encoding ASCII
    Write-Host "Wrote $localProps"
}

if (-not (Test-Path $model)) {
    Write-Host "Downloading pose_landmarker_full.task"
    python (Join-Path $root "scripts\download_pose_landmarker.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download pose landmarker model"
    }
}

$gradlew = Join-Path $android "gradlew.bat"
Push-Location $android
try {
    & $gradlew assembleDebug --stacktrace
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle assembleDebug failed"
    }
}
finally {
    Pop-Location
}

python (Join-Path $root "scripts\check_apk_16kb.py") $apk
if ($LASTEXITCODE -ne 0) {
    throw "16 KB alignment check failed"
}

Write-Host "APK: $apk"

$adb = Join-Path $sdk "platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCmd) {
        $adb = $adbCmd.Source
    } else {
        Write-Host "adb not found; skip install. Copy the APK to the phone or install platform-tools."
        exit 0
    }
}

$devices = & $adb devices
$ready = @($devices | Select-Object -Skip 1 | Where-Object { $_ -match '\tdevice$' })
if ($ready.Count -eq 0) {
    Write-Host "No adb device in 'device' state. Enable USB debugging on the S26, then:"
    Write-Host "  $adb install -r `"$apk`""
    exit 0
}

& $adb install -r $apk
if ($LASTEXITCODE -ne 0) {
    throw "adb install failed"
}
Write-Host "Installed on $($ready.Count) device(s). Open Visual Pose and allow camera."
