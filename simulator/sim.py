#!/usr/bin/env python3
"""Pokretanje simulatora iz bilo kog foldera: python simulator/sim.py run primer"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from eurosim.__main__ import main  # noqa: E402

sys.exit(main())
