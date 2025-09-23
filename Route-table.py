"""
Sanitized script — no hard-coded secrets.
All credentials/paths come from environment variables (use .env locally).

Environment variables used:
- MYSQL_URL            : SQLAlchemy URL (mysql+pymysql://user:pass@host:3306/schema)
- SSH_DEFAULT_USERNAME : default SSH username for device access
- SSH_DEFAULT_PASSWORD : default SSH password for device access
- CREDENTIALS_JSON     : optional JSON list of credential objects for multi-try connections
- DEVICES_CSV          : path to a file containing device IPs (one per line)
- DEVICES              : comma/newline separated device IPs (fallback if DEVICES_CSV missing)
- HOSTNAME_INPUT_DIR   : directory path with .txt files to parse
- OUTPUT_DIR           : output folder for generated CSVs

Security notes:
- Copy `.env.example` -> `.env` and fill locally. Never commit `.env`.
- Consider a secrets manager for production.
"""
#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
from datetime import datetime
import os
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import paramiko
from dotenv import load_dotenv

load_dotenv()

# Load devices from file if present, else from DEVICES env var
devices_file = os.getenv("DEVICES_CSV", "devices.txt")
if os.path.exists(devices_file):
    with open(devices_file, encoding="utf-8") as f:
        devices = [l.strip() for l in f if l.strip()]
else:
    devices_raw = os.getenv("DEVICES", "")
    devices = [d.strip() for d in devices_raw.replace(",", "\n").splitlines() if d.strip()]

if not devices:
    print("No devices provided. Add IPs to devices.txt or set DEVICES env var.")
    devices = []

device_type = os.getenv("DEFAULT_DEVICE_TYPE", "juniper")
username = os.getenv("SSH_DEFAULT_USERNAME")
password = os.getenv("SSH_DEFAULT_PASSWORD")

if not (username and password):
    print("WARNING: SSH_DEFAULT_USERNAME / SSH_DEFAULT_PASSWORD not set. Connection will fail.")

netmiko_exceptions = (
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
    paramiko.ssh_exception.SSHException,
    ConnectionResetError,
    OSError,
    IndexError,
    EOFError
)

filedate_lo = datetime.now().strftime('loopback-%H')
filedate_nni = datetime.now().strftime('nni-%H')

for device in devices:
    try:
        print('~' * 60, f"Connecting to {device} for /32", sep="\n")
        conn = ConnectHandler(ip=device, device_type=device_type, username=username, password=password, timeout=30)
        output = conn.send_command('show route protocol ldp | match /32 | except 224.0.0.2/32 ')
        with open(filedate_lo + ".txt", "w", encoding="utf-8") as fh:
            fh.write(output)
        conn.disconnect()
    except netmiko_exceptions as e:
        print('Failed:', device, e)

for device in devices:
    try:
        print('~' * 60, f"Connecting to {device} for /30", sep="\n")
        conn = ConnectHandler(ip=device, device_type=device_type, username=username, password=password, timeout=30)
        output = conn.send_command('show route table inet.0 | match /30')
        with open(filedate_nni + ".txt", "w", encoding="utf-8") as fh:
            fh.write(output)
        conn.disconnect()
    except netmiko_exceptions as e:
        print('Failed:', device, e)
