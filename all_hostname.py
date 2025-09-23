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
import json
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
import paramiko
import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

mysql_url = os.getenv("MYSQL_URL")
if not mysql_url:
    raise SystemExit("MYSQL_URL not set. Put it in .env.")

engine = create_engine(mysql_url)
# Expect a table 'loopback_ip' with column 'ip' (case-insensitive).
df = pd.read_sql("SELECT ip FROM loopback_ip", engine)
devices = df['ip'].dropna().astype(str).unique().tolist()

# Credentials: either JSON array or fallback to default envs
creds_raw = os.getenv("CREDENTIALS_JSON", "[]")
credentials = []
try:
    credentials = json.loads(creds_raw)
except Exception:
    credentials = []

if not credentials:
    username = os.getenv("SSH_DEFAULT_USERNAME")
    password = os.getenv("SSH_DEFAULT_PASSWORD")
    if not (username and password):
        raise SystemExit("No credentials provided. Set SSH_DEFAULT_USERNAME/SSH_DEFAULT_PASSWORD or CREDENTIALS_JSON.")
    credentials = [
        {"device_type": "huawei", "username": username, "password": password, "command": "display inventory device ne-id 1"},
        {"device_type": "juniper", "username": username, "password": password, "command": "show version"},
        {"device_type": "zte_zxros", "username": username, "password": password, "command": "show hostname"},
    ]

netmiko_exceptions = (
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
    paramiko.ssh_exception.SSHException,
    ConnectionResetError,
    OSError,
    IndexError,
    EOFError
)

def try_connect(ip: str) -> bool:
    for cred in credentials:
        try:
            print(f"[{ip}] trying {cred['device_type']} ...")
            conn = ConnectHandler(
                host=ip,
                device_type=cred["device_type"],
                username=cred["username"],
                password=cred["password"],
                timeout=30
            )
            output = conn.send_command(cred["command"])
            with open(f"{ip}.txt", "w", encoding="utf-8") as fh:
                fh.write(output)
            conn.disconnect()
            print(f"[{ip}] success, output saved to {ip}.txt")
            return True
        except netmiko_exceptions as e:
            print(f"[{ip}] failed with {cred['device_type']}: {e}")
        except Exception as e:
            print(f"[{ip}] unexpected error: {e}")
    return False

failed = []
for ip in devices:
    if not try_connect(ip):
        failed.append(ip)

if failed:
    out_csv = f"failed_ip_{datetime.now().strftime('%Y-%m-%d')}.csv"
    pd.DataFrame(failed, columns=["Failed IP"]).to_csv(out_csv, index=False)
    print(f"Saved failed IPs to {out_csv}")
else:
    print("All devices succeeded.")
