1.Заходим в командную строку
2.Скачать гит
3.Скачать питон 3.12

4.Создаем папку и переходим в нее и выполняем команду:
git clone https://github.com/Danil01042005/speech-transcriber.git
5. cd speech-transcriber
6. cd speech_app

Далее в зависимости от системы:

Windows - PowerShell
python -m venv .venv 
.venv\Scripts\activate.bat    или .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app_gui.py


Linux / macOS (bash)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
sudo apt install python3-tk libasound-dev portaudio19-dev
python -m pip install -r requirements.txt
python app_gui.py