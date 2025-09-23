# Network Automation

Network automation tools: hostname extraction, route/NNI/loopback parsing, and SSH collectors for Huawei/Juniper/ZTE.
All secrets are loaded from environment variables — see `.env.example`.

## Setup (Windows 11)

```powershell
# 1) Clone
cd %USERPROFILE%\Documents
mkdir GitHub
cd GitHub
git clone https://github.com/Tahmidjawad/network-automation.git
cd network-automation

# 2) Create venv + install deps
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3) Configure secrets
copy .env.example .env   # then edit .env with your values
```

## Usage

```powershell
python hostname_info.py
python db-write-route-table.py
python Route-table.py
python all_hostname.py
```

- `devices.txt` can contain one IP per line (or set `DEVICES` env var).
- Input directory for hostname parsing is `HOSTNAME_INPUT_DIR` (see `.env.example`).
- Output CSVs are written to `OUTPUT_DIR`.

## Security
- Never commit `.env`. Keep credentials local or use a secret manager.
- Scripts include comments describing which environment variables they use.
