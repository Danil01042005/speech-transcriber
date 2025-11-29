cd path/to/cloudapi          # или path\to\cloudapi на Windows

# Windows PowerShell
python -m venv .venv         # py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install grpcio-tools pyaudio
python app_gui.py

# Linux / macOS (bash)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install grpcio-tools pyaudio
python app_gui.py