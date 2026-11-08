#!/bin/sh
# Eurosim (simulator i editor taktika) iz ovog repoa, bez instaliranja Python-a.
# Prvi put uv skine Python i biblioteke (~1 min, treba internet); posle radi i bez interneta.
# Uvek je ovo najnovija verzija iz repoa: posle "git pull" (ili Repo -> Pull latest u aplikaciji) samo ponovo pokreni.
cd "$(dirname "$0")" || exit 1
UV=$(command -v uv 2>/dev/null)
[ -z "$UV" ] && [ -x .tools/uv ] && UV=.tools/uv
if [ -z "$UV" ]; then
  echo "Treba uv (jedan fajl, bez admin prava): https://docs.astral.sh/uv/"
  printf "Da ga skinem u .tools/ u ovom repou? [d/N] "
  read -r a
  case "$a" in d|D|y|Y) ;; *) exit 1 ;; esac
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$PWD/.tools" UV_NO_MODIFY_PATH=1 sh || exit 1
  UV=.tools/uv
fi
exec "$UV" run --project simulator python simulator/sim.py serve "$@"
