# Ulaz za izvršni fajl (PyInstaller) i za "python simulator/eurosim_main.py".
# Bez argumenata: web interfejs (otvara browser). Sa argumentima: kao sim.py (run, robot, serve, list).
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()          # simulacije rade u posebnim procesima (spawn)
    from eurosim.__main__ import main
    sys.exit(main(sys.argv[1:] or ["serve"]))
