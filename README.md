```
git clone https://github.com/Danil01042005/speech-transcriber.git
cd speech-transcriber
```

```
cd speech-transcriber/speech_app
```

**Windows PowerShell**
```
python -m venv .venv         # py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app_gui.py
```

**Linux / macOS (bash)**
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app_gui.py
```