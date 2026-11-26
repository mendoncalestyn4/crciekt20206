"""Build "Cricket Captain Stats Pack.exe" (stage 5) on a Windows machine:

    python tools/build_program.py [run number]

1. desktop/build.json: the version (the date and the run number, e.g. 2026.11.27.3), the code's fingerprint (so a new
   version always gets its kept answers worked out afresh) and every version's notes (design/WHATS_NEW.json).
2. PyInstaller makes dist/Cricket Captain Stats Pack/ (the .exe and its parts, the site's pages inside).
3. dist/<name>-<version>.zip and dist/latest.json (its size and fingerprint) for the updates repository."""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = "Cricket Captain Stats Pack"
sys.path.insert(0, str(ROOT))


def main(run: str = "0") -> None:
    from ccstats.keep import code_fingerprint
    today = datetime.date.today()
    version = f"{today:%Y.%m.%d}.{int(run)}"
    history = json.loads((ROOT / "design" / "WHATS_NEW.json").read_text(encoding="utf-8"))
    if history and not history[0].get("version"):
        history[0] = dict(history[0], version=version, date=f"{today.day} {today:%b %Y}")
    info = {"version": version, "date": f"{today.day} {today:%b %Y}", "code": code_fingerprint(ROOT), "history": history}
    (ROOT / "desktop" / "build.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    sep = ";" if sys.platform == "win32" else ":"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
                    "--name", NAME, "--icon", str(ROOT / "desktop" / "icon" / "stats-pack.ico"),
                    "--paths", str(ROOT),
                    "--add-data", f"{ROOT / 'web' / 'dist'}{sep}web/dist",
                    "--add-data", f"{ROOT / 'desktop' / 'build.json'}{sep}desktop",
                    "--collect-submodules", "ccstats", "--collect-submodules", "server",
                    "--collect-submodules", "desktop", "--collect-submodules", "uvicorn",
                    "--exclude-module", "streamlit", "--exclude-module", "plotly", "--exclude-module", "matplotlib",
                    "--exclude-module", "pytest", "--exclude-module", "playwright",
                    str(ROOT / "tools" / "program_entry.py")], check=True, cwd=ROOT)
    folder = ROOT / "dist" / NAME
    zname = f"{NAME.replace(' ', '-')}-{version}.zip"
    zpath = ROOT / "dist" / zname
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, pathlib.Path(NAME) / f.relative_to(folder))
    data = zpath.read_bytes()
    latest = {"version": version, "date": info["date"], "file": zname, "size": len(data),
              "sha256": hashlib.sha256(data).hexdigest(), "notes": history[0]["notes"] if history else []}
    (ROOT / "dist" / "latest.json").write_text(json.dumps(latest, indent=1), encoding="utf-8")
    print(f"built {zname}: {len(data) / 1e6:.0f} MB")


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["0"]))
