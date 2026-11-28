#!/usr/bin/env python3
"""Pokretanje simulatora iz bilo kog foldera:

    python studio/sim.py serve          # web interfejs
    python studio/sim.py run primer     # komandna linija
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

if __name__ == "__main__":                 # i zaštita za multiprocessing (spawn ponovo uvozi ovaj fajl)
    from eurosim.__main__ import main
    sys.exit(main())
