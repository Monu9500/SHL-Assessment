"""
Fail fast when users run the API with conda/base Python while backend/.venv exists.

This prevents the confusing sklearn/numpy ABI crash during Uvicorn's reload subprocess.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def backend_root() -> Path:
    # app/runtime_bootstrap.py -> backend/
    return Path(__file__).resolve().parents[1]


def venv_python_if_present() -> Path | None:
    root = backend_root()
    if os.name == "nt":
        p = root / ".venv" / "Scripts" / "python.exe"
    else:
        p = root / ".venv" / "bin" / "python"
    return p if p.exists() else None


def _looks_like_conda_or_anaconda_python() -> bool:
    exe = Path(sys.executable).as_posix().lower()
    return any(x in exe for x in ("anaconda3", "miniconda3", "miniconda", "mambaforge", "micromamba"))


def enforce_known_good_runtime() -> None:
    """
    If backend/.venv exists, require that exact interpreter (unless opted out via env var).
    If .venv is missing but conda python is used, print a one-time warning.
    """
    if os.environ.get("TALENTLENS_ALLOW_ANY_PYTHON") == "1":
        return

    want = venv_python_if_present()
    cur = Path(sys.executable).resolve()

    if want is None:
        if _looks_like_conda_or_anaconda_python():
            print(
                "\n[TalentLens] You are using a conda-based Python and no backend/.venv was found.\n"
                "Create an isolated venv (recommended):\n"
                f"  cd \"{backend_root()}\"\n"
                "  python -m venv .venv\n"
                "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
                "  python start_api.py\n",
                file=sys.stderr,
            )
        return

    if cur.resolve() == want.resolve():
        return

    root = backend_root()
    print("\n" + "=" * 78, file=sys.stderr)
    print("WRONG PYTHON INTERPRETER (this is why imports crash under Uvicorn reload).", file=sys.stderr)
    print(f"  You ran:     {cur}", file=sys.stderr)
    print(f"  Required:    {want.resolve()}", file=sys.stderr)
    print("\nDo this instead:", file=sys.stderr)
    print(f'  cd "{root}"', file=sys.stderr)
    print("  python start_api.py", file=sys.stderr)
    print("  (or double-click backend\\run_uvicorn.cmd)", file=sys.stderr)
    print("\nDo NOT run `python -m uvicorn ...` while conda (base) is on PATH.", file=sys.stderr)
    print("Optional escape hatch (not recommended): set TALENTLENS_ALLOW_ANY_PYTHON=1", file=sys.stderr)
    print("=" * 78 + "\n", file=sys.stderr)
    raise SystemExit(2)
