"""
Start FastAPI with backend/.venv — even if you run this file using conda (base) python.

Usage (from anywhere):
  python path/to/backend/start_api.py

Or after: cd backend
  python start_api.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent


def venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    return BACKEND_ROOT / ".venv" / "bin" / "python"


def ensure_venv() -> Path:
    py = venv_python()
    if py.exists():
        return py
    print("Creating .venv …")
    subprocess.check_call([sys.executable, "-m", "venv", str(BACKEND_ROOT / ".venv")], cwd=BACKEND_ROOT)
    if not py.exists():
        raise SystemExit("Could not create .venv. Install Python 3.12+ and retry.")
    return py


def ensure_deps(py: Path) -> None:
    print("Verifying backend import inside .venv ...", flush=True)
    proc = subprocess.run(
        [str(py), "-c", "import app.main"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return
    if proc.stdout:
        print(proc.stdout, end="", flush=True)
    if proc.stderr:
        print(proc.stderr, end="", flush=True)
    print("Installing dependencies into .venv (first run can take several minutes) …", flush=True)
    subprocess.check_call([str(py), "-m", "pip", "install", "-U", "pip", "wheel"], cwd=BACKEND_ROOT)
    subprocess.check_call([str(py), "-m", "pip", "install", "-r", "requirements.txt"], cwd=BACKEND_ROOT)


def main() -> int | None:
    parser = argparse.ArgumentParser(description="Start the TalentLens AI backend.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Start the server with auto-reload enabled (development mode).",
    )
    args = parser.parse_args()

    py = ensure_venv()
    target = py.resolve()
    current = Path(sys.executable).resolve()

    if current != target:
        print(
            "\n[!] Avoided conda/global Python for the server.\n"
            f"    Using: {target}\n"
            f"    (You ran: {current})\n"
        )
        ensure_deps(py)
        cmd = [
            str(target),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
        if args.reload:
            cmd.append("--reload")
        print("Launching backend server in .venv ...", flush=True)
        return subprocess.call(cmd, cwd=BACKEND_ROOT)

    ensure_deps(py)
    import uvicorn

    print("\nAPI: http://127.0.0.1:8000/health\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=args.reload)
    return None


if __name__ == "__main__":
    code = main()
    if isinstance(code, int):
        raise SystemExit(code)
