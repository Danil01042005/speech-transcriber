1. Установите Git и Python (рекомендуется Python 3.12).

2. В терминале выполните:

```
git clone https://github.com/Danil01042005/speech-transcriber.git
cd speech-transcriber/speech_app
```

3. Запустите команды для своей системы:

**Windows / PowerShell**
```
python -m venv .venv
.venv\Scripts\activate.bat    # или .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app_gui.py
```

**Linux / macOS (bash)**
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
sudo apt install python3-tk libasound-dev portaudio19-dev
python -m pip install -r requirements.txt
python app_gui.py
```