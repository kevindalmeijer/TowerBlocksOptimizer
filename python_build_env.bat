@echo off
python -m venv env
call env\Scripts\activate
python -m pip install pip --upgrade
python -m pip install -r python_requirements.txt
