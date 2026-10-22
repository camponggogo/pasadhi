"""Autostart for four platforms. Generates the files; only --apply touches the system.

    Windows  Task Scheduler XML (AtStartup) or schtasks
    Linux    systemd user unit + `systemctl --user enable`
    macOS    LaunchAgent plist + launchctl load
    Android  Foreground Service + BOOT_COMPLETED (source snippet; the APK is built by the app project)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def windows_task(python_exe: str, script: str, user: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>PASADHI compute service</Description></RegistrationInfo>
  <Triggers><BootTrigger><Enabled>true</Enabled><Delay>PT1M</Delay></BootTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{user}</UserId><LogonType>InteractiveToken</LogonType>
    <RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries></Settings>
  <Actions Context="Author"><Exec><Command>{python_exe}</Command>
    <Arguments>"{script}" --port 8765</Arguments></Exec></Actions>
</Task>
"""


def systemd_unit(python_exe: str, script: str) -> str:
    return f"""[Unit]
Description=PASADHI compute service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_exe} {script} --port 8765
Restart=on-failure
RestartSec=5
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7

[Install]
WantedBy=default.target
"""


def launch_agent(python_exe: str, script: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>online.campong.pasadhi</string>
  <key>ProgramArguments</key><array>
    <string>{python_exe}</string><string>{script}</string><string>--port</string><string>8765</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
"""


ANDROID_SNIPPET = """// Android: one foreground service, started at boot.
class PasadhiService : Service() {
    override fun onCreate() {
        startForeground(1, NotificationCompat.Builder(this, "pasadhi")
            .setContentTitle("PASADHI กำลังแชร์ทรัพยากร")
            .setSmallIcon(R.drawable.ic_stat).build())
        // bind to the Rust/JNI core here; the same share sliders live in the app's Settings screen
    }
    override fun onBind(intent: Intent?) = null
}

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED)
            ContextCompat.startForegroundService(context, Intent(context, PasadhiService::class.java))
    }
}
// AndroidManifest: RECEIVE_BOOT_COMPLETED, FOREGROUND_SERVICE, FOREGROUND_SERVICE_DATA_SYNC
"""


def write(target_dir: Path, python_exe: str, script: str, user: str = '') -> dict:
    target_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    if sys.platform == 'win32':
        path = target_dir / 'pasadhi-task.xml'
        path.write_text(windows_task(python_exe, script, user or 'INTERACTIVE'), encoding='utf-16')
        files['task_xml'] = str(path)
        files['install'] = f'schtasks /Create /TN "PASADHI" /XML "{path}" /F'
    elif sys.platform == 'darwin':
        path = target_dir / 'online.campong.pasadhi.plist'
        path.write_text(launch_agent(python_exe, script), encoding='utf-8')
        files['plist'] = str(path)
        files['install'] = (f'cp "{path}" ~/Library/LaunchAgents/ && '
                            f'launchctl load ~/Library/LaunchAgents/online.campong.pasadhi.plist')
    else:
        path = target_dir / 'pasadhi.service'
        path.write_text(systemd_unit(python_exe, script), encoding='utf-8')
        files['unit'] = str(path)
        files['install'] = (f'mkdir -p ~/.config/systemd/user && cp "{path}" ~/.config/systemd/user/ && '
                            f'systemctl --user daemon-reload && systemctl --user enable --now pasadhi.service')
    android = target_dir / 'android-foreground-service.kt'
    android.write_text(ANDROID_SNIPPET, encoding='utf-8')
    files['android_snippet'] = str(android)
    return files


def apply(files: dict) -> bool:
    if 'install' not in files:
        return False
    result = subprocess.run(files['install'], shell=True, capture_output=True, text=True)
    return result.returncode == 0
