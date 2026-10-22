# PASADHI App — แอปเดียว ทำได้ทุก role

**สถานะ: M1.5 prototype รันได้จริง** · โค้ด: `pasadhi/app/` · ภาพหน้าจอ: `pasadhi/app/ui-screenshot.png`

> เป้าหมาย: ผู้ใช้ติดตั้งครั้งเดียว จบ — ไม่ต้องเลือกเองว่าเป็น client/worker/coordinator
> แอปตัดสินใจให้ พร้อมเหตุผลที่อ่านรู้เรื่อง และผู้ใช้ยัง override ได้ทุกเมื่อ

---

## 1. สถาปัตยกรรม: process เดียว สามบทบาท

```
┌──────────────────────────────────────────────┐
│  pasadhi-app (service)                       │
│  ├─ probe      อ่านสเปกเครื่องตอนติดตั้ง/บูต  │
│  ├─ roles      ให้คะแนน → coordinator/worker  │
│  ├─ budget     แปลง % เป็นเพดานจริง           │
│  ├─ worker     duty-cycle ตามเพดาน CPU       │
│  ├─ ui         หน้าตั้งค่า 127.0.0.1:8765     │
│  └─ autostart  Task Scheduler/systemd/launchd │
└──────────────────────────────────────────────┘
```

`client` = โหมดเบาที่สุด (ไม่แชร์อะไร ใช้เรียก API เท่านั้น) · `worker` = แชร์ตามเพดาน ·
`coordinator` = รับงาน + เก็บ topology (เครื่องที่ออนไลน์ตลอด)

## 2. เลือก role อัตโนมัติ (ให้คะแนน ไม่ใช่สุ่ม)

| ปัจจัย | คะแนน | ตัวอย่างที่วัดได้ |
|---|---|---:|
| logical cores (สูงสุด 16) | +1 ต่อ core | 8 → +8 |
| RAM (สูงสุด 64 GB) | +1 ต่อ 4 GB | 15.9 GB → +4.0 |
| พื้นที่ว่าง (สูงสุด 2 TB) | +1 ต่อ 100 GB | 43 GB → +0.4 |
| GPU (ตาม VRAM) | +1.2 ต่อ GB | GTX 1050 2 GB → +2.4 |
| เครือข่าย ≥1 GbE / ≥100 Mb | +4 / +2 | 4.3 Gb/s → +4 |
| uptime ≥7 วัน / ≥1 วัน | +4 / +2 | 88 ชม. → +2 |
| ใช้แบตเตอรี่ | −6 | — |

**เกณฑ์:** coordinator ถ้า score ≥ 20 และ cores ≥ 4, RAM ≥ 8, uptime ≥ 24 ชม., link ≥ 100 Mb
· worker ถ้า cores ≥ 2 และ RAM ≥ 4 · ที่เหลือเป็น client

ตัวอย่างจริงจากเครื่องทดสอบ: **score 18.2 → worker** (8 threads, 15.9 GB, uptime 88 ชม.)

## 3. หน้าตั้งค่า: 5 สไลเดอร์ + รายได้สด

![หน้าจอ](ui-screenshot.png)

| สไลเดอร์ | เพดาน | สิ่งที่บังคับใช้จริง |
|---|---:|---|
| CPU | 0–90 % | duty cycle: ทำงาน `duty × 100 ms` แล้วพักที่เหลือ |
| GPU | 0–100 % | เฉพาะเครื่องที่มี NVIDIA (ตรวจด้วย `nvidia-smi`) |
| RAM | 0–80 % | เพดานหน่วยความจำที่ worker ขอได้ |
| HDD | 0–50 % | พื้นที่แคช/บล็อกที่ให้ใช้ |
| Network | 0–80 % | เพดานแบนด์วิดท์ต่อชั่วโมง |

ตั้งแล้วมีผลทันที (POST `/api/share` → worker อ่านค่าใหม่ในลูปถัดไป) ไม่ต้องรีสตาร์ท

## 4. รายได้: จาก % → บาท

```
rates  CPU 0.55 ฿/core-ชม. · RAM 0.035 ฿/GB-ชม. · GPU 0.90 ฿/ชม. (ต่อ 2 GB) · HDD 0.05 ฿/GB-เดือน
ตัวอย่าง 8 threads / 15.9 GB ที่ CPU 35 %, RAM 20 %, HDD 10 %
  → 2.8 cores × 0.55 = 1.54 ฿/ชม.
    3.18 GB × 0.035 = 0.11 ฿/ชม.
    รวม ≈ 1.65 ฿/ชม. = 39.6 ฿/วัน = 1,189 ฿/เดือน
```

อัตรานี้อ้างจาก `commercial/token_model.py` (credit 2.5 ฿/node-ชม. สำหรับเครื่อง 4c/8GB เต็ม) —
ตรวจซ้ำได้ด้วย `python pasadhi/app/budget.py` (ได้ 2.484 ฿/ชม. ที่ 100 %)

## 5. Token ประจำเครื่อง

- สร้างครั้งแรกตอนติดตั้ง: 32 ตัวอักษร (ไม่มีตัวที่อ่านสับสน), แสดงเป็น `my43-ezgk••••••tzm8`
- เก็บที่ `%LOCALAPPDATA%\pasadhi\identity.json` (Windows) หรือ `~/.config/pasadhi/` (Linux)
  `~/Library/Application Support/pasadhi/` (macOS) — ตั้งสิทธิ์เฉพาะผู้ใช้ (`icacls` / `chmod 600`)
- `device_id = psd_` + sha256(token)[:16] · เซิร์ฟเวอร์เก็บแค่ hash ไม่เก็บ token ดิบ
- ปุ่ม "ออก Token ใหม่" = rotate ทันที (token เก่าใช้ไม่ได้)
- ลายเซ็นคำขอ = HMAC-SHA256(token, payload) — ไม่ใช่รหัสผ่าน และไม่ใช้ซ้ำข้ามเครื่อง

## 6. Autostart 4 แพลตฟอร์ม

| OS | กลไก | ไฟล์ที่สร้าง | คำสั่งติดตั้ง |
|---|---|---|---|
| Windows | Task Scheduler (AtStartup, delay 1 นาที) | `pasadhi-task.xml` | `schtasks /Create /TN PASADHI /XML … /F` |
| Linux | systemd user unit (`Restart=on-failure`) | `pasadhi.service` | `systemctl --user enable --now pasadhi.service` |
| macOS | LaunchAgent (`RunAtLoad`, `KeepAlive`) | `online.campong.pasadhi.plist` | `launchctl load …` |
| Android | Foreground Service + `BOOT_COMPLETED` | `android-foreground-service.kt` | รวมใน APK |

`python pasadhi/app/install.py --autostart` จะ **เขียนไฟล์ให้** และพยายามติดตั้งให้ (ต้องสิทธิ์ผู้ใช้) —
บน Windows ต้องรันแบบ admin ถ้าจะสร้าง task ระดับเครื่อง

## 7. แพ็กเกจ/build ที่ต้องทำต่อ

| แพลตฟอร์ม | รูปแบบ | เครื่องมือ |
|---|---|---|
| Windows | `.msi` + portable zip | WiX หรือ Tauri bundler |
| Linux | `.deb` + AppImage | `cargo-deb`, AppImage builder |
| macOS | `.dmg` (notarized) | Tauri + `codesign`/`notarytool` |
| Android | `.apk` / `.aab` | Gradle + Rust JNI (core เดียวกัน) |

**คำแนะนำสถาปัตยกรรม:** ย้าย core (probe/roles/budget/worker) ไปเป็น Rust crate เดียว
แล้วให้ UI เป็น Tauri 2 (ใช้ HTML ชุดนี้ได้เลย) — ได้ binary เดียวต่อแพลตฟอร์ม, ใช้ memory น้อย,
และ Android ใช้ crate เดิมผ่าน JNI ได้โดยไม่ต้องเขียน logic ซ้ำ

## 8. ความปลอดภัยที่ต้องมีก่อนปล่อยจริง

- [ ] token เก็บใน OS keychain (DPAPI/Keychain/Keystore) ไม่ใช่ไฟล์ plaintext
- [ ] TLS pinning ไปยัง coordinator + signed manifest ของงาน
- [ ] auto-update ที่ลงนาม (Ed25519) และ rollback ได้
- [ ] sandbox งานที่รับมา (Windows Job Object / Linux cgroup / macOS sandbox) — worker ต้องไม่เห็นไฟล์ผู้ใช้
- [ ] audit log ฝั่งเครื่อง: ทุกงานที่รับ/ส่ง พร้อม checksum
- [ ] uninstall ที่ลบ identity + autostart + cache ครบ

## 9. สิ่งที่วัดได้แล้วในรอบนี้

| รายการ | ผล |
|---|---|
| probe | 210.8 ms (Windows 11, 8 threads, 15.9 GB, Radeon 530) |
| role | worker, score 18.2 พร้อมเหตุผลรายบรรทัด |
| UI | ตั้ง 35/0/20/10/20 → 1,189 ฿/เดือน, อัปเดตทันที |
| token | สร้าง/rotate ได้, mask แสดงผล |
| autostart | สร้าง Task Scheduler XML + Android snippet สำเร็จ |
