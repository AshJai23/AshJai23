# Start SmartInvest with F5

Open the **projects/smartinvest-ai** folder itself in VS Code (File → Open Folder). Install Python 3.12 and the recommended Microsoft Python/Python Debugger extensions. Select **Run and Debug → SmartInvest: FastAPI**, then press **F5**.

The pre-launch tasks create a project-local .venv, install requirements.lock.txt, and install the project. Windows uses `py -3.12`; macOS/Linux use `python3.12`. Dependencies require internet; installation can take several minutes. Then Uvicorn runs on 127.0.0.1:8000 with access logging disabled. Open http://127.0.0.1:8000/ in your browser; /docs provides API documentation. Keep VS Code running; stop the debug session to stop the server.

If port 8000 is occupied, change the port argument in .vscode/launch.json to 8001 and open that port instead. Setup tasks recheck dependencies on each launch; no global Python packages or system execution policies are modified. Do not commit your .venv or sensitive input data.

These configuration files were JSON-validated; the equivalent Linux install/test/Uvicorn commands were exercised in the assistant workspace. The Windows/macOS launch branches and graphical VS Code debugger were not executed here. This does not install anything on your computer until you open the project and run the task. It is local development, not a publicly hosted service.
