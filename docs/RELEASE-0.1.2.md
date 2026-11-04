# PASADHI 0.1.2 source bundles

Fix first-run earnings persistence on Linux and macOS, also applied to Android/Termux and source bundles. Create the destination directory at every save and keep the worker alive after an OSError, retrying at the next save interval.

These packages derive from the shipped 0.1.1 Python bundles; Windows standalone remains 0.1.1. Linux startup is verified through WSL with a fresh config directory. macOS shares the faulty code and its config-path behavior is covered; native macOS execution is not claimed.

Input archive SHA-256:

- linux: `586663c0dcecbc48087ec05017b8b410f4cdb3806c5b91e7466b8f3192b60f1c`
- macos: `5fed9969b666ea2ac1d6e6cfe2605da04fa90416674762f9fbc397642ff6c3b8`
- android-termux: `d938f7494ece5ccb92b8ef06e7c56b049ad2f333ab71282e14388d368050e130`
- source: `c328f6fb0c2dd6bddabde8cdc5a6ae0f88def977735c09e331efc30e3f51b184`
