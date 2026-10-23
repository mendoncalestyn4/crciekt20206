"""The Stats Pack zip from the committed code (HEAD): the program only, in a 'Cricket Captain Stats Pack' folder.

    python3 tools/build_zip.py <repo> <out.zip>

It holds the current site (app.py, ccstats, ui, views), the new site (server and the built website in web/dist) and
their launchers. Never the tests, the design mock-ups, the website's source or its build tools (node_modules)."""
import io
import subprocess
import sys
import zipfile

FILES = {".streamlit/config.toml", "README.md", "ROADMAP.md", "NEW_SITE_PLAN.md", "Start Stats Pack.bat",
         "Start new Stats Pack (preview).bat", "app.py", "requirements.txt"}


def keep(name: str) -> bool:
    top = name.split("/")[0]
    return (name in FILES or (top in ("ccstats", "ui", "views", "server") and name.endswith(".py"))
            or name.startswith("web/dist/"))


def main(repo: str, out: str) -> None:
    raw = subprocess.run(["git", "-C", repo, "archive", "--format=zip", "HEAD"], capture_output=True, check=True).stdout
    src = zipfile.ZipFile(io.BytesIO(raw))
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.comment = head.encode()
        for info in src.infolist():
            if info.is_dir() or not keep(info.filename):
                continue
            z.writestr("Cricket Captain Stats Pack/" + info.filename, src.read(info))
            n += 1
    print(n, "files", head)


if __name__ == "__main__":
    main(*sys.argv[1:3])
