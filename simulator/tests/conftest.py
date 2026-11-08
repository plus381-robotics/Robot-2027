# Testovi simulatora: python -m pytest simulator/tests
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import os, tempfile                                                 # noqa: E401,E402
# testovi ne diraju korisnikov ~/.eurosim.json (zapamćen repo, plan S10)
os.environ.setdefault("EUROSIM_CONFIG", os.path.join(tempfile.mkdtemp(prefix="eurosim-cfg-"), "eurosim.json"))
