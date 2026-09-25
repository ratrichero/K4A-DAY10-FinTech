@echo off
echo ======================================================================
echo    VINUNI AI-ENGINEER K4 - DAY 10 RAG DATA OBSERVABILITY STUDIO
echo ======================================================================
echo Dang khoi dong Web Dashboard Streamlit tai http://localhost:8501 ...
echo Nhan Ctrl+C de dung ung dung bat cu luc nao.
echo ======================================================================

set PYTHONIOENCODING=utf-8
.\.venv\Scripts\python.exe -m streamlit run src/app.py --server.port 8501 --server.fileWatcherType none
pause
