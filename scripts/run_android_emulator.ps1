# Create/start the Visual Pose Android emulator, then build and install the debug APK.
$ErrorActionPreference = "Stop"

$AvdName = "VisualPoseApi35"
$SystemImage = "system-images;android-35;google_apis;x86_64"

function Find-JavaHome {
    if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
        return $env:JAVA_HOME
    }
    $candidates = @((Join-Path $env:LOCALAPPDATA "jdk-17"))
    $candidates += @(Get-ChildItem "C:\Program Files\Microsoft\jdk-17*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    $candidates += @(Get-ChildItem "C:\Program Files\Eclipse Adoptium\jdk-17*" -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    foreach ($dir in $candidates) {
        if ($dir -and (Test-Path (Join-Path $dir "bin\java.exe"))) {
            return $dir
        }
    }
    return $null
}

$javaHome = Find-JavaHome
if (-not $javaHome) {
    throw "JDK 17 not found. Set JAVA_HOME or install Microsoft OpenJDK 17."
}
$env:JAVA_HOME = $javaHome
$env:Path = "$(Join-Path $javaHome 'bin');" + $env:Path

$root = Split-Path -Parent $PSScriptRoot
$sdk = $env:ANDROID_HOME
if (-not $sdk -or -not (Test-Path $sdk)) {
    $sdk = $env:ANDROID_SDK_ROOT
}
if (-not $sdk -or -not (Test-Path $sdk)) {
    $sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
}
if (-not (Test-Path $sdk)) {
    throw "Android SDK not found. Set ANDROID_HOME."
}
$env:ANDROID_HOME = $sdk
$env:ANDROID_SDK_ROOT = $sdk
$env:Path = "$(Join-Path $sdk 'platform-tools');$(Join-Path $sdk 'emulator');$(Join-Path $sdk 'cmdline-tools\latest\bin');" + $env:Path

$sdkmanager = Join-Path $sdk "cmdline-tools\latest\bin\sdkmanager.bat"
$avdmanager = Join-Path $sdk "cmdline-tools\latest\bin\avdmanager.bat"
$emulator = Join-Path $sdk "emulator\emulator.exe"
$adb = Join-Path $sdk "platform-tools\adb.exe"

if (-not (Test-Path $emulator) -or -not (Test-Path (Join-Path $sdk "system-images\android-35\google_apis\x86_64"))) {
    Write-Host "Installing emulator + $SystemImage"
    cmd /c "`"$sdkmanager`" --sdk_root=$sdk --install `"emulator`" `"$SystemImage`""
    if ($LASTEXITCODE -ne 0) {
        throw "sdkmanager install failed"
    }
}

$avdHome = Join-Path $env:USERPROFILE ".android\avd"
$avdIni = Join-Path $avdHome "$AvdName.ini"
if (-not (Test-Path $avdIni)) {
    Write-Host "Creating AVD $AvdName"
    $create = "echo no | `"$avdmanager`" create avd -n $AvdName -k `"$SystemImage`" -d pixel_7 --force"
    cmd /c $create
    if ($LASTEXITCODE -ne 0) {
        throw "avdmanager create avd failed"
    }
    $config = Join-Path $avdHome "$AvdName.avd\config.ini"
    if (Test-Path $config) {
        $ini = Get-Content $config
        $ini = $ini | ForEach-Object {
            if ($_ -match '^hw\.camera\.back=') { "hw.camera.back=virtualscene" }
            elseif ($_ -match '^hw\.camera\.front=') { "hw.camera.front=none" }
            else { $_ }
        }
        Set-Content -Path $config -Value $ini
    }
}

function Get-ReadyEmulators {
    $lines = & $adb devices
    return @($lines | Select-Object -Skip 1 | Where-Object { $_ -match '^emulator-.*\tdevice$' })
}

if ((Get-ReadyEmulators).Count -eq 0) {
    Write-Host "Starting emulator $AvdName (virtual scene camera)..."
    Start-Process -FilePath $emulator -ArgumentList @(
        "-avd", $AvdName,
        "-camera-back", "virtualscene",
        "-camera-front", "none",
        "-gpu", "auto",
        "-netdelay", "none",
        "-netspeed", "full"
    ) | Out-Null
}

Write-Host "Waiting for emulator boot..."
$deadline = (Get-Date).AddMinutes(8)
do {
    Start-Sleep -Seconds 5
    $ready = Get-ReadyEmulators
    $booted = $false
    if ($ready.Count -gt 0) {
        $prop = & $adb shell getprop sys.boot_completed 2>$null
        $booted = ($prop -match "1")
    }
    if ((Get-Date) -gt $deadline) {
        throw "Emulator did not boot within 8 minutes. Check Windows Hypervisor Platform / WHPX."
    }
} while (-not $booted)

Write-Host "Emulator ready. Building and installing APK..."
powershell -File (Join-Path $root "scripts\build_android_apk.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "build_android_apk.ps1 failed"
}

& $adb shell pm grant local.visual.corepose android.permission.CAMERA
& $adb shell am start -n local.visual.corepose/.MainActivity
Write-Host "Visual Pose launched. Emulator uses the virtual scene camera (a 3D room)."
Write-Host "For a real person, enable a PC webcam in the emulator ... Camera menu, or pass -camera-back webcam0."
Write-Host "Logcat: adb logcat -s CorePose:I *:E"
