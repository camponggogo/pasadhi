"""The local settings page: five sliders, a live earnings number, one token, one autostart switch."""

PAGE = """<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PASADHI · ปัสสัทธิ</title>
<style>
:root{--bg:#0f1412;--panel:#171f1b;--line:#2c3830;--lime:#d1ff68;--ink:#ecf0e6;--muted:#9aa89d;--warn:#e0b070}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:28px 22px 60px}
header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:16px}
h1{font-size:20px;margin:0;letter-spacing:-.02em}h1 span{color:var(--lime)}
.badge{font-size:11px;padding:6px 12px;border-radius:20px;background:#22301f;color:var(--lime);border:1px solid #47603a}
.grid{display:grid;grid-template-columns:1.15fr 1fr;gap:18px;margin-top:22px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 18px 14px}
.card h2{font-size:12px;letter-spacing:.14em;color:var(--muted);margin:0 0 14px;text-transform:uppercase}
.row{display:grid;grid-template-columns:86px 1fr 72px;gap:12px;align-items:center;margin:12px 0}
.row label{font-size:13px;color:#cfd8cb}
input[type=range]{width:100%;accent-color:var(--lime)}
output{font-variant-numeric:tabular-nums;text-align:right;color:var(--lime);font-weight:600}
.money{font-size:40px;letter-spacing:-.03em;color:var(--lime);margin:4px 0 0}
.money small{font-size:13px;color:var(--muted);letter-spacing:0}
.sub{font-size:12px;color:var(--muted);margin:6px 0 0}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
td{padding:5px 0;border-bottom:1px solid #212b24;color:#c8d2c4}td:last-child{text-align:right;color:var(--ink)}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#cbd6c6}
button{background:#22301f;color:var(--lime);border:1px solid #47603a;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer}
button:hover{background:#2b3d26}
.switch{display:flex;align-items:center;gap:10px;margin-top:10px}
.note{font-size:11.5px;color:var(--muted);margin-top:10px;line-height:1.7}
.foot{margin-top:18px;font-size:11px;color:#6f7d72}
</style></head><body><div class="wrap">
<header><h1>PASADHI <span>· ปัสสัทธิ</span></h1><div class="badge" id="role">role: …</div></header>

<div class="grid">
  <div class="card">
    <h2>แชร์ทรัพยากรของเครื่องนี้</h2>
    <div class="row"><label>CPU</label><input id="cpu" type="range" min="0" max="90" step="5"><output id="cpu_o"></output></div>
    <div class="row"><label>GPU</label><input id="gpu" type="range" min="0" max="100" step="10"><output id="gpu_o"></output></div>
    <div class="row"><label>RAM</label><input id="ram" type="range" min="0" max="80" step="5"><output id="ram_o"></output></div>
    <div class="row"><label>HDD</label><input id="disk" type="range" min="0" max="50" step="5"><output id="disk_o"></output></div>
    <div class="row"><label>Network</label><input id="network" type="range" min="0" max="80" step="5"><output id="net_o"></output></div>
    <div class="switch"><input id="autostart" type="checkbox"><label for="autostart">เริ่มอัตโนมัติเมื่อเปิดเครื่อง</label></div>
    <p class="note">เพดาน CPU สูงสุด 90% · RAM 80% · HDD 50% · Network 80% เพื่อให้เครื่องยังใช้งานปกติได้
    ค่าที่ตั้งจะมีผลทันทีกับ worker ที่กำลังทำงาน</p>
  </div>

  <div class="card">
    <h2>รายได้ของคุณ (ประมาณการ)</h2>
    <p class="money"><span id="monthly">0</span> <small>บาท / เดือน</small></p>
    <p class="sub">≈ <span id="daily">0</span> บาท/วัน · <span id="hourly">0</span> บาท/ชั่วโมง</p>
    <table>
      <tr><td>CPU</td><td id="b_cpu">–</td></tr>
      <tr><td>GPU</td><td id="b_gpu">–</td></tr>
      <tr><td>RAM</td><td id="b_ram">–</td></tr>
      <tr><td>HDD</td><td id="b_disk">–</td></tr>
      <tr><td>เพดานที่ให้ใช้</td><td id="limits">–</td></tr>
    </table>
    <p class="note">ตัวเลขนี้คือ credit ที่ใช้ลดค่าบริการได้ 1 credit = 1 บาท · เพดานลดได้ 50% ของบิล</p>
  </div>
</div>

<div class="card" style="margin-top:18px">
  <h2>Token ของเครื่องนี้</h2>
  <p class="mono" id="device">–</p>
  <p class="mono" id="token">–</p>
  <div class="switch"><button id="rotate">ออก Token ใหม่</button><span class="sub" id="rotated"></span></div>
  <p class="note">Token ถูกสร้างครั้งแรกตอนติดตั้ง เก็บในเครื่องนี้เท่านั้น (สิทธิ์ไฟล์เฉพาะผู้ใช้) —
  ใช้ยืนยันตัวเครื่องกับ coordinator ไม่ใช่รหัสผ่าน</p>
</div>

<p class="foot" id="hardware">–</p>
</div>
<script>
const $ = id => document.getElementById(id);
const keys = ['cpu','gpu','ram','disk','network'];
let state = null;

function paint(s){
  state = s;
  $('role').textContent = 'role: ' + s.role + ' · score ' + s.score;
  const sh = s.share;
  $('cpu').value = sh.cpu_pct; $('gpu').value = sh.gpu_pct; $('ram').value = sh.ram_pct;
  $('disk').value = sh.disk_pct; $('network').value = sh.network_pct;
  $('cpu_o').textContent = sh.cpu_pct + '%'; $('gpu_o').textContent = sh.gpu_pct + '%';
  $('ram_o').textContent = sh.ram_pct + '%'; $('disk_o').textContent = sh.disk_pct + '%';
  $('net_o').textContent = sh.network_pct + '%';
  $('autostart').checked = !!s.autostart;
  const e = s.earnings, b = e.breakdown;
  $('monthly').textContent = Math.round(e.monthly_thb).toLocaleString('th-TH');
  $('daily').textContent = e.daily_thb.toFixed(1);
  $('hourly').textContent = e.hourly_thb.toFixed(2);
  $('b_cpu').textContent = b.cpu.toFixed(2) + ' ฿/ชม.';
  $('b_gpu').textContent = b.gpu.toFixed(2) + ' ฿/ชม.';
  $('b_ram').textContent = b.ram.toFixed(3) + ' ฿/ชม.';
  $('b_disk').textContent = b.disk.toFixed(3) + ' ฿/ชม.';
  const l = s.limits;
  $('limits').textContent = l.cpu_cores + ' cores · ' + l.ram_gb + ' GB RAM · ' + l.disk_gb + ' GB disk';
  $('device').textContent = 'device  ' + s.identity.device_id;
  $('token').textContent = 'token   ' + s.identity.token_masked;
  const h = s.hardware;
  $('hardware').textContent = h.os + ' · ' + h.cpu_model + ' · ' + h.cores_logical + ' threads · '
    + h.ram_gb + ' GB RAM' + (h.has_gpu ? (' · ' + h.gpu_name + ' ' + h.gpu_vram_gb + ' GB') : ' · no NVIDIA GPU')
    + ' · uptime ' + h.uptime_hours.toFixed(0) + ' h · probe ' + h.probe_ms + ' ms';
}

async function load(){ paint(await (await fetch('/api/state')).json()); }

async function push(){
  const body = {cpu_pct:+$('cpu').value, gpu_pct:+$('gpu').value, ram_pct:+$('ram').value,
                disk_pct:+$('disk').value, network_pct:+$('network').value};
  paint(await (await fetch('/api/share',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)})).json());
}

keys.forEach(k => $(k).addEventListener('input', () => {
  $(k + '_o').textContent = $(k).value + '%';
}));
keys.forEach(k => $(k).addEventListener('change', push));
$('autostart').addEventListener('change', async e => {
  paint(await (await fetch('/api/autostart',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({enabled:e.target.checked})})).json());
});
$('rotate').addEventListener('click', async () => {
  paint(await (await fetch('/api/rotate',{method:'POST'})).json());
  $('rotated').textContent = 'สร้างใหม่แล้ว — token เก่าใช้ไม่ได้อีก';
});
load(); setInterval(load, 5000);
</script></body></html>
"""
