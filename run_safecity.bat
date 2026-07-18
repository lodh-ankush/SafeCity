@echo off
cd /d "c:\Users\KIIT0001\Downloads\SafeCityAI\safecity_env"
call Scripts\activate.bat
echo Virtual environment activated.
echo Running SafeCityAI Pipeline...
echo.
python safecity_pipeline.py
echo.
echo =============================
echo Pipeline run complete.
echo =============================
pause
