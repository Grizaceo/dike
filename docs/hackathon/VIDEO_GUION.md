# Video Script & Recording Guide — Diké (2–3 minutes, English)

> **Target duration:** 2:15 – 2:45  
> **Language:** Spoken narration in **English**; CLI output and JSON fields in **Spanish** (explicitly noted in narration).  
> **Automated terminal runner:** `scripts/hackathon/demo_video.sh`

---

## How to Record in One Command

From the repository root (`~/dike` or the profile), in a clean terminal window:

```bash
# Option A — Run the complete sequence with a 2-second pause between scenes (for screen recording / OBS):
PAUSA=2 bash scripts/hackathon/demo_video.sh

# Option B — Record an asciinema cast:
asciinema rec -c "PAUSA=2 bash scripts/hackathon/demo_video.sh" /tmp/dike_demo.cast

# Option C — Run inside the offline Docker container (network completely disabled):
docker run --rm --network none dike bash scripts/hackathon/demo_video.sh
```

`scripts/hackathon/demo_video.sh` creates an isolated temporary workspace under `/tmp/dike-video-XXXXXX`, unsets any real signing key variables, runs all 5 scenes against the local `chile-base` corpus (`pack_hash` `af1422d66d1e6eee`), and cleans up on exit.

---

## Scene-by-Scene Script, Exact Commands & Expected Output

### Scene 1 (0:00 – 0:25) — The Problem & The Synthetic Brief

**Narration (EN):**
> "Legal AI tools fail when they over-claim—hallucinating statutes or certifying citations they cannot verify. Diké does the opposite: *verify less, prove it*. All CLI outputs and statutory texts are in Spanish. Here is `escrito_demo.md`, a synthetic Chilean labor brief with six statutory citations: four real articles from the Labor Code, one ambiguous citation with no statute named, and one article that does not exist."

**Exact Command:**
```bash
cat docs/hackathon/escrito_demo.md
```

**Expected Output:**
```text
EN LO PRINCIPAL: demanda por despido improcedente. (Escrito SINTÉTICO de demostración; partes ficticias.)

S. J. L. DEL TRABAJO DE SANTIAGO

A. B. C., trabajadora, a US. respetuosamente digo:

PRIMERO.- La demandada puso término a mi contrato invocando la causal de necesidades de la empresa del artículo 161 del Código del Trabajo.

SEGUNDO.- El artículo 162 del Código del Trabajo dispone que, cuando el empleador invoque esa causal, el aviso deberá darse al trabajador, con copia a la Inspección del Trabajo respectiva, a lo menos con treinta días de anticipación.

TERCERO.- Conforme al artículo 163 del Código del Trabajo, si el contrato hubiere estado vigente un año o más y el empleador le pusiere término por necesidades de la empresa, deberá pagar la indemnización por años de servicio.

CUARTO.- El artículo 168 del Código del Trabajo permite al trabajador que considere improcedente la aplicación de la causal recurrir al juzgado competente, dentro del plazo de sesenta días hábiles contado desde la separación.

QUINTO.- A mayor abundamiento, el artículo 60 obliga al empleador a lo solicitado.

SEXTO.- Lo anterior se refuerza con el artículo 9999 del Código del Trabajo.
```

---

### Scene 2 (0:25 – 1:05) — `dike constancia` & Explicit Refusal (`AMBIGUOUS` / `UNRESOLVABLE`)

**Narration (EN):**
> "We run `dike constancia` completely offline against a local, content-addressed snapshot of 25 Chilean statutes (`pack_hash` `af1422d66d1e6eee`). Diké verifies Articles 161, 162, 163, and 168 of the Labor Code, and exits with code 1 because it refuses to certify the other two: *artículo 60* is rejected as `AMBIGUOUS` because that article number exists in multiple codes and no statute was named; *artículo 9999 del Código del Trabajo* is rejected as `UNRESOLVABLE` because it does not exist in the corpus."

**Exact Commands:**
```bash
python -m lexo_cli constancia docs/hackathon/escrito_demo.md --origen 'demanda laboral (demo)'
python -m lexo_cli constancia docs/hackathon/escrito_demo.md --json | jq '{meta: .meta, rechazadas: [.detalles[] | select(.estado != "VERIFICADA") | {cita_raw, estado, resolucion}]}'
```

**Expected Output (Table + JSON summary):**
```text
✕ CONSTANCIA DE VERIFICACIÓN — CON PROBLEMAS
Documento: docs/hackathon/escrito_demo.md
Origen: demanda laboral (demo)
Fecha: 2026-10-27T...Z · Pack: af1422d66d1e6eee
...
Resumen: 4/6 citas verificadas
(exit code: 1 — non-zero because 2 citations could not be verified)
```
```json
{
  "meta": {
    "documento": "docs/hackathon/escrito_demo.md",
    "origen": null,
    "as_of": "2026-10-26",
    "fecha_constancia": "2026-10-27T...Z",
    "pack_hash": "af1422d66d1e6eee",
    "total_citas": 6,
    "citas_verificadas": 4,
    "citas_fallidas": 2
  },
  "rechazadas": [
    {
      "cita_raw": "artículo 60",
      "estado": "FALLO",
      "resolucion": "AMBIGUOUS"
    },
    {
      "cita_raw": "artículo 9999 del Código del Trabajo",
      "estado": "FALLO",
      "resolucion": "UNRESOLVABLE"
    }
  ]
}
```

---

### Scene 3 (1:05 – 1:40) — The Signed Commitment & What It Does Not Claim

**Narration (EN):**
> "With `--emit-commitment` and `--sign`, Diké emits `commitment.json` and `commitment.sig.json`. The commitment uses a closed schema: it contains only the four verified provisions with their source text SHA-256 hashes, `pack_hash`, and the counts—`citas_verificadas: 4`, `citas_fallidas: 2`. Neither the brief's prose, nor its file path, nor the two rejected citations enter the commitment. And inside `alcance` and `advertencias`, the commitment states its own limit: it attests reference identity, source-text integrity, provenance, and in-force status in the local snapshot—not whether the statute substantively supports the lawyer's argument. The other limits are Diké's, stated in the kit and in the video: the signature does not prove signer identity, and it is not an accredited legal timestamp under Chilean Law 19.799."

**Exact Commands:**
```bash
jq . docs/hackathon/commitment.json
jq . docs/hackathon/commitment.sig.json
cat docs/hackathon/content-signing-key.pub
```

**Expected Output:**
```json
{
  "_aviso_huella_omitida": "document_sha256 y document_bytes omitidos por defecto. La huella del escrito no viaja en este compromiso.",
  "advertencias": [
    "Diké verifica que estas normas existan, sean citables y estén vigentes; NO verifica que fundamenten sustantivamente lo que el escrito afirma.  Esa fundamentación es juicio del abogado."
  ],
  "alcance": "La constancia acredita identidad de la referencia, integridad del texto fuente, provenance y vigencia; no certifica la corrección de interpretaciones o paráfrasis.",
  "as_of": "2026-10-26",
  "citas_fallidas": 2,
  "citas_verificadas": 4,
  "fecha_constancia": "2026-10-27T00:24:30Z",
  "normas_verificadas": [
    {
      "cuerpo": "Código del Trabajo art. 161",
      "estado": "VERIFICADA",
      "fuente_url": "https://nuevo.leychile.cl/servicios/Navegar/get_norma_json?idNorma=207436",
      "gid": "cl.norma.ct:art:0161",
      "texto_hash": "0c3c636d5119921c80a08c59dc81ef5d953220c465c0de555a261f2412325e88",
      "vigencia": "IN_FORCE",
      "vigencia_legible": "vigente"
    },
    "... (arts. 0162, 0163, 0168) ..."
  ],
  "pack_hash": "af1422d66d1e6eee",
  "schema_version": "dike-constancia-commitment-v2",
  "total_citas": 6
}
```
```json
{
  "algorithm": "ed25519",
  "commitment_hash": "d220a00f21b317279a95a40a643232637645d526c3a63684f90381f7b7f45c30",
  "key_id": "3c7b3fde075efbe3",
  "role": "content-integrity",
  "schema_version": "dike-content-signature-v2",
  "signature": "b68935b31dce8dfb5bb30f3660dc7e9c6898fb46359cb7596fe8a8feda72d64ea15643c633c9a4b748f7fcc7fc36f5287cf7b3d2f8b6316f14799b719456210c"
}
```

---

### Scene 4 (1:40 – 2:15) — Third-Party Verification (With and Without Python)

**Narration (EN):**
> "Anyone can verify this commitment offline without trusting or importing Diké's code. First, `verificar_tercero.py` uses only Python's standard library and `cryptography`. Second, we don't even need Python: using the recipe in `KEYS.md`, `jq` canonicalizes the JSON, `sha256sum` computes the commitment hash and the role-bound payload `content-integrity:ed25519:dike-content-signature-v2:<hash>`, and `openssl pkeyutl -verify` checks the Ed25519 signature against `key_id` `3c7b3fde075efbe3`."

**Exact Commands:**
```bash
cd docs/hackathon
python3 verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub
# Followed by the literal jq + sha256sum + basenc + openssl pkeyutl recipe from KEYS.md:
```

**Expected Output:**
```text
1. Contrato declarado por el sobre
   schema_version: dike-content-signature-v2
   role          : content-integrity
   algorithm     : ed25519
   => OK

2. Hash canónico del commitment
   calculado : d220a00f21b317279a95a40a643232637645d526c3a63684f90381f7b7f45c30
   firmado   : d220a00f21b317279a95a40a643232637645d526c3a63684f90381f7b7f45c30
   => OK

3. Identidad de la llave (key_id = 16 hex del SHA-256 de la pubkey en bruto)
   calculado  : 3c7b3fde075efbe3
   en el sobre: 3c7b3fde075efbe3
   => OK

4. Firma Ed25519 sobre sha256(role:algorithm:schema_version:hash), en hex
   => VÁLIDA

RESULTADO: VERIFICADO
```
And for Path 2 (`jq` + OpenSSL 3, zero Python):
```text
key_id: 3c7b3fde075efbe3
Signature Verified Successfully
```

---

### Scene 5 (2:15 – 2:40) — Negative Control & Closing on Abstention

**Narration (EN):**
> "Finally, `demo_bli_e2e.py` runs the full cycle including a negative control: if someone alters `citas_verificadas` from 4 to 6 and `citas_fallidas` from 2 to 0, verification immediately fails with `exit 1` (`NO COINCIDE`). And the demo ends not on a hash, but on what Diké refused to certify. Because the contract—commitment, `pack_hash`, and explicit abstention—is jurisdiction-agnostic, any legal corpus packaged in this format inherits the same offline verification."

**Exact Command:**
```bash
python docs/hackathon/demo_bli_e2e.py
```

**Expected Output (Closing Section):**
```text
[5/5] Control negativo: se altera un número del commitment
      citas_verificadas 4 -> 6, citas_fallidas 2 -> 0  (como si todo hubiera pasado)
      exit 1
      => NO COINCIDE: el commitment cambió después de firmarse

========================================================================
LO QUE DIKÉ SE NEGÓ A CERTIFICAR
========================================================================
  ✕ «artículo 60»
      AMBIGUOUS: no dice de qué cuerpo legal es; ese número existe en más de un código
  ✕ «artículo 9999 del Código del Trabajo»
      UNRESOLVABLE: esa norma no está en el corpus: no hay texto ni vigencia que verificar

  Ninguna de las dos está en el commitment firmado. De ellas solo viaja
  un número: citas_fallidas = 2.
  Y las 4 que sí pasaron prueban que la norma existe, es citable y
  está vigente. No que diga lo que el escrito le atribuye: eso no lo
  verifica Diké, y el commitment lo declara en su campo `alcance`.
========================================================================
```
