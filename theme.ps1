# theme.ps1 — переключение Windows light/dark темы через реестр.
# После изменения реестра бродкастим WM_SETTINGCHANGE через user32,
# чтобы тема применилась мгновенно без перезапуска приложений.
#
# Параметры:
#   -Action get              вывести текущий режим (light/dark)
#   -Action set -Mode light  переключить на light
#   -Action set -Mode dark   переключить на dark

param(
    [ValidateSet("get", "set")]
    [string]$Action = "get",
    [ValidateSet("light", "dark", "")]
    [string]$Mode = ""
)

$ErrorActionPreference = "Stop"
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class ThemeBroadcast {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    private static extern IntPtr SendMessageTimeout(
        IntPtr hWnd, uint Msg, IntPtr wParam, string lParam,
        uint flags, uint timeout, out IntPtr result);

    public static void NotifyThemeChanged() {
        const int HWND_BROADCAST = 0xffff;
        const uint WM_SETTINGCHANGE = 0x001A;
        const uint SMTO_ABORTIFHUNG = 0x0002;
        IntPtr result;
        SendMessageTimeout(
            (IntPtr)HWND_BROADCAST,
            WM_SETTINGCHANGE,
            IntPtr.Zero,
            "ImmersiveColorSet",
            SMTO_ABORTIFHUNG,
            100,
            out result);
    }
}
"@

function Get-CurrentMode {
    $sys = (Get-ItemProperty -Path $RegPath -Name SystemUsesLightTheme -ErrorAction Stop).SystemUsesLightTheme
    $app = (Get-ItemProperty -Path $RegPath -Name AppsUseLightTheme -ErrorAction Stop).AppsUseLightTheme
    if ($sys -eq 1 -and $app -eq 1) { return "light" }
    return "dark"
}

function Set-ThemeMode([string]$Mode) {
    $value = if ($Mode -eq "light") { 1 } else { 0 }
    Set-ItemProperty -Path $RegPath -Name SystemUsesLightTheme -Value $value -Type DWord
    Set-ItemProperty -Path $RegPath -Name AppsUseLightTheme -Value $value -Type DWord
    [ThemeBroadcast]::NotifyThemeChanged()
}

if ($Action -eq "get") {
    $mode = Get-CurrentMode
    Write-Output $mode
    exit 0
}

if ($Action -eq "set") {
    if (-not $Mode) {
        Write-Error "ERROR: -Mode light|dark required"
        exit 10
    }
    Set-ThemeMode $Mode
    $mode = Get-CurrentMode
    Write-Output "OK:$mode"
    exit 0
}