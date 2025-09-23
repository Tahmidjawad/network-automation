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
import os
import re
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

directory = os.getenv("HOSTNAME_INPUT_DIR", r"D:\Network_Database\Hostname")
output_dir = os.getenv("OUTPUT_DIR", ".")
os.makedirs(output_dir, exist_ok=True)

all_data = []
current_date = datetime.now().strftime('%Y-%m-%d')

if not os.path.isdir(directory):
    print(f"Directory not found: {directory}. Set HOSTNAME_INPUT_DIR.")
else:
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()

            ip = os.path.splitext(filename)[0]

            # Huawei
            huawei_hostname = re.search(r'NeName=<([^>]+)>', content)
            huawei_model = re.search(r'NeType=<([^>]+)>', content)
            if huawei_hostname and huawei_model:
                all_data.append([ip, huawei_hostname.group(1), huawei_model.group(1), 'Huawei'])
                continue

            # Juniper
            juniper_hostname = re.search(r'(?:Hostname:\s+|set system host-name\s+)([^\n]+)', content)
            juniper_model = re.search(r'Model:\s+([^\n]+)', content)
            if juniper_hostname and juniper_model:
                all_data.append([ip, juniper_hostname.group(1), juniper_model.group(1), 'Juniper'])
                continue

            # ZTE
            zte_hostname = re.search(r'#\s*show hostname\s*\n(\S+)', content)
            zte_model = re.search(r'ZXCTN\s+(\S+)', content)
            if zte_hostname and zte_model:
                model_name = f'ZXCTN {zte_model.group(1)}'
                all_data.append([ip, zte_hostname.group(1), model_name, 'ZTE'])

df_all = pd.DataFrame(all_data, columns=['IP', 'Hostname', 'Model', 'Vendor'])

zte_df = df_all[df_all['Vendor'] == 'ZTE']
zte_csv_path = os.path.join(output_dir, f'ZTE_Hostname_{current_date}.csv')
df_all_csv_path = os.path.join(output_dir, f'hostname_ip_{current_date}.csv')
zte_df.to_csv(zte_csv_path, index=False)
df_all.to_csv(df_all_csv_path, index=False)
print(f"Wrote CSVs:\n  {zte_csv_path}\n  {df_all_csv_path}")

mysql_url = os.getenv("MYSQL_URL")
if mysql_url:
    engine = create_engine(mysql_url)
    df_all.to_sql('hostname_ip', con=engine, if_exists='replace', index=False)
    print("DB: replaced table 'hostname_ip'")
else:
    print("MYSQL_URL not set — DB write skipped.")
