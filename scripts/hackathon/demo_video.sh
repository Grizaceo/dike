#!/usr/bin/env bash
# Secuencia reproducible en terminal limpia para grabar el video del BUIDL
# (BLI Legal Tech Hackathon 2 — DoraHacks 1904).
#
# Uso:
#   bash scripts/hackathon/demo_video.sh
#   PAUSA=2 bash scripts/hackathon/demo_video.sh   # pausa entre escenas (seg)
#   asciinema rec -c "PAUSA=2 bash scripts/hackathon/demo_video.sh" dike_demo.cast
#
# No usa llaves privadas reales ni red, y no escribe fuera de /tmp.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

PAUSA="${PAUSA:-0}"
WORK="$(mktemp -d /tmp/dike-video-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

export TMPDIR="$WORK/tmp"
export HERMES_HOME="$WORK/hermes"
export DIKE_HITL_DB="$WORK/events.db"
export DIKE_ROOTS_CACHE_DIR="$WORK/roots_cache"
export DIKE_BINDING_CACHE_DIR="$WORK/binding_cache"
export PYTHONDONTWRITEBYTECODE=1
unset LEXO_CONTENT_SIGNING_KEY_PATH LEXO_CUSTODY_SIGNING_KEY_PATH
mkdir -p "$TMPDIR" "$HERMES_HOME" "$DIKE_ROOTS_CACHE_DIR" "$DIKE_BINDING_CACHE_DIR"

if [ -x "$HOME/.local/share/lexo-cli-venv/bin/python" ]; then
  PY="$HOME/.local/share/lexo-cli-venv/bin/python"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import lexo_cli.commands.constancia, pydantic, cryptography" >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1 && python -c "import lexo_cli.commands.constancia, pydantic, cryptography" >/dev/null 2>&1; then
  PY="python"
else
  echo "ERROR: no se encontró intérprete Python con las dependencias de Diké instaladas" >&2
  exit 1
fi

# Seleccionar usuario con corpus instalado (tu-nombre en host o demo en contenedor)
if [ -z "${DIKE_USER:-}" ]; then
  if [ -d "$HOME/.dike/users/tu-nombre" ]; then
    export DIKE_USER="tu-nombre"
  elif [ -d "$HOME/.dike/users/demo" ]; then
    export DIKE_USER="demo"
  fi
fi

banner() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

run_cmd() {
  echo "\$ $*"
  "$@"
}

pausa() {
  if [ "$PAUSA" != "0" ]; then
    sleep "$PAUSA"
  fi
}

# ── ESCENA 1: El escrito sintético (6 citas) ─────────────────────────────
banner "SCENE 1 — Synthetic Chilean labor brief (6 statutory citations)"
run_cmd cat docs/hackathon/escrito_demo.md
pausa

# ── ESCENA 2: dike constancia y las 2 citas rechazadas ───────────────────
banner "SCENE 2 — dike constancia: 4 verified, 2 refused (AMBIGUOUS / UNRESOLVABLE)"
echo "\$ python -m lexo_cli constancia docs/hackathon/escrito_demo.md --origen 'demanda laboral (demo)'"
set +e
"$PY" -m lexo_cli constancia docs/hackathon/escrito_demo.md --origen "demanda laboral (demo)"
RC=$?
set -e
echo "(exit code: $RC — non-zero because 2 citations could not be verified)"
[ "$RC" -eq 1 ] || { echo "ERROR: se esperaba exit 1 y salió $RC"; exit 1; }

echo ""
echo "\$ python -m lexo_cli constancia docs/hackathon/escrito_demo.md --json | jq '{meta: .meta, rechazadas: [.detalles[] | select(.estado != \"VERIFICADA\") | {cita_raw, estado, resolucion}]}'"
set +e
"$PY" -m lexo_cli constancia docs/hackathon/escrito_demo.md --json > "$WORK/constancia.json"
RC_JSON=$?
set -e
[ "$RC_JSON" -eq 1 ] || { echo "ERROR: se esperaba exit 1 en --json y salió $RC_JSON"; exit 1; }
jq '{meta: .meta, rechazadas: [.detalles[] | select(.estado != "VERIFICADA") | {cita_raw, estado, resolucion}]}' "$WORK/constancia.json"
pausa

# ── ESCENA 3: El commitment firmado publicado en el kit ──────────────────
banner "SCENE 3 — Signed commitment (commitment.json + commitment.sig.json)"
run_cmd jq . docs/hackathon/commitment.json
echo ""
run_cmd jq . docs/hackathon/commitment.sig.json
echo ""
run_cmd cat docs/hackathon/content-signing-key.pub
pausa

# ── ESCENA 4: Verificación por un tercero (con y sin Python) ─────────────
banner "SCENE 4A — Third-party verification Path 1 (verificar_tercero.py, zero Diké imports)"
(
  cd docs/hackathon
  echo "\$ python3 verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub"
  "$PY" verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub
)
pausa

banner "SCENE 4B — Third-party verification Path 2 (NO Python: jq + coreutils + OpenSSL 3)"
"$PY" - <<'PYEOF' > "$WORK/camino2.sh"
import re
from pathlib import Path
texto = Path("docs/hackathon/KEYS.md").read_text(encoding="utf-8")
bloques = re.findall(r"^```bash\n(.*?)^```", texto, flags=re.DOTALL | re.MULTILINE)
recetas = [b for b in bloques if "openssl pkeyutl" in b]
assert len(recetas) == 1, f"se esperaba 1 receta OpenSSL, hay {len(recetas)}"
print(recetas[0], end="")
PYEOF
(
  cd docs/hackathon
  echo "\$ # Running the literal jq + sha256sum + basenc + openssl pkeyutl recipe from KEYS.md"
  bash "$WORK/camino2.sh"
)
pausa

# ── ESCENA 5: Control negativo y demo E2E (cierra en la abstención) ──────
banner "SCENE 5 — Negative control (tampered commitment rejected) & E2E abstention summary"
"$PY" docs/hackathon/demo_bli_e2e.py --out "$WORK/e2e"
