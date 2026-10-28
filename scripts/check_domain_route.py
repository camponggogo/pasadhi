"""Read-only DNS and existing vhost diagnostics."""
from pathlib import Path
from urllib.request import urlopen
import socket,re,paramiko
print('pasadhi.tech IPv4:',socket.gethostbyname_ex('pasadhi.tech')[2])
with urlopen('https://pasadhi.tech/',timeout=20) as r:
    body=r.read().decode('utf-8'); print('HTTPS title:',re.findall(r'<title>(.*?)</title>',body,re.S)[:1]);print('Final URL:',r.url)
c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('187.52.120.204',username='root',key_filename=str(Path.home()/'.ssh/ssh_hostinger_deploy'),timeout=30,allow_agent=False,look_for_keys=False)
try:
    for command in ['cat /etc/nginx/sites-available/pasadhi.tech', "curl --silent --max-time 10 -H 'Host: pasadhi.tech' http://127.0.0.1/ | head -c 500"]:
        _,out,err=c.exec_command(command);print(out.read().decode());print(err.read().decode())
finally:c.close()
