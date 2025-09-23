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
import glob
import pandas as pd
import jtextfsm as textfsm
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

tabledate = datetime.now().strftime('%Y-%m-%d')

# ---- Parse NNI (/30) from files matching n*.txt with template agg12.templ ----
filedate_nni = datetime.now().strftime('nni-%Y-%m-%d.csv')
list_of_dataframes = []
for filename in glob.glob("n*.txt"):
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        raw_text_data = f.read()
    with open("agg12.templ", "r", encoding="utf-8", errors="ignore") as template:
        re_table = textfsm.TextFSM(template)
        fsm_results = re_table.ParseText(raw_text_data)
        df = pd.DataFrame(fsm_results)
        df['SourceFile'] = os.path.splitext(os.path.basename(filename))[0]
        list_of_dataframes.append(df)

if list_of_dataframes:
    nniip = pd.concat(list_of_dataframes, ignore_index=True)
    nniip['UpdateDate'] = tabledate
    # Expecting three columns from template; normalize names:
    nniip = nniip.iloc[:, :2] if nniip.shape[1] >= 2 else pd.DataFrame(columns=["IP","Hour"])
    nniip.columns = ["IP", "Hour"]
    nniip["IP"] = nniip["IP"].astype(str).str.replace("/30", "", regex=False)
    nniip2 = nniip.drop_duplicates('IP', keep='last')[['IP']].copy()
    nniip2['UpdateDate'] = tabledate
    nniip2.to_csv(filedate_nni, index=False)
    print(f"NNI CSV written: {filedate_nni} ({len(nniip2)} rows)")
else:
    nniip2 = pd.DataFrame(columns=["IP", "UpdateDate"])
    print("No NNI files (n*.txt) found. Skipping NNI CSV.")

# ---- Parse Loopback (/32) from files matching l*.txt with template loopback.templ ----
filedate_lo = datetime.now().strftime('loopback-%Y-%m-%d.csv')
list_of_dataframes = []
for filename in glob.glob("l*.txt"):
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        raw_text_data = f.read()
    with open("loopback.templ", "r", encoding="utf-8", errors="ignore") as template:
        re_table = textfsm.TextFSM(template)
        fsm_results = re_table.ParseText(raw_text_data)
        df = pd.DataFrame(fsm_results)
        df['SourceFile'] = os.path.splitext(os.path.basename(filename))[0]
        list_of_dataframes.append(df)

if list_of_dataframes:
    loopback = pd.concat(list_of_dataframes, ignore_index=True)
    loopback['UpdateDate'] = tabledate
    loopback = loopback.iloc[:, :2] if loopback.shape[1] >= 2 else pd.DataFrame(columns=["IP","Hour"])
    loopback.columns = ["IP", "Hour"]
    loopback["IP"] = loopback["IP"].astype(str).str.replace("/32", "", regex=False)
    loopback2 = loopback.drop_duplicates('IP', keep='last')[['IP']].copy()
    loopback2['UpdateDate'] = tabledate
    loopback2 = loopback2[loopback2['IP'].ne("")]
    loopback2.to_csv(filedate_lo, index=False)
    print(f"Loopback CSV written: {filedate_lo} ({len(loopback2)} rows)")
else:
    loopback2 = pd.DataFrame(columns=["IP", "UpdateDate"])
    print("No Loopback files (l*.txt) found. Skipping loopback CSV.")

# ---- Write to MySQL if configured ----
mysql_url = os.getenv("MYSQL_URL")
if not mysql_url:
    print("WARNING: MYSQL_URL not set — database write skipped.")
else:
    engine = create_engine(mysql_url)
    with engine.begin() as conn:
        if not loopback2.empty:
            loopback2.to_sql('loopback_ip', con=conn, if_exists='append', index=False)
            print("DB: appended loopback_ip")
        if not nniip2.empty:
            nniip2.to_sql('nni_ip', con=conn, if_exists='append', index=False)
            print("DB: appended nni_ip")
