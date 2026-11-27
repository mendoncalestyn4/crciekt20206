"""The program's starting point for PyInstaller (tools/build_program.py): "Cricket Captain Stats Pack.exe".

freeze_support() first: the site prepares pages with helper processes, and in a packaged Windows program each helper
is this same .exe started again; without it a helper would run the whole program instead of its share of the work
(found by the real update test on Windows, 27 November: the helpers never finished, so the program never closed)."""
import multiprocessing

multiprocessing.freeze_support()

from desktop.program import main  # noqa: E402

raise SystemExit(main())
