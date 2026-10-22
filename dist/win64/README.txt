PASADHI 0.1.0 - Windows portable build
=====================================

Run:      double-click PASADHI.bat
Settings: http://127.0.0.1:8765
Config:   %LOCALAPPDATA%\pasadhi\  (identity token + config + earnings)

The app probes this machine, picks a role by itself (coordinator / worker / client),
then shows five share sliders and a live earnings estimate.

Requirements: Python 3.10 or newer on PATH, and the psutil package (installed on first run).

Autostart: open the settings page, tick "start automatically", or run
  python -m pasadhi.app.install --autostart

Uninstall: delete this folder and %LOCALAPPDATA%\pasadhi
