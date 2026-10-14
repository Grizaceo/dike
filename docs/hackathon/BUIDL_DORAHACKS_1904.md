# DoraHacks BUIDL Submission — BLI Legal Tech Hackathon 2 (Hackathon 1904)

> Ready-to-paste submission text in English. Every claim below is backed by an existing reproducible command in the repository.

---

## Form Fields

- **BUIDL Title:** `Diké — Verify Less, Prove It: Offline Statutory Citation Commitments`
- **Tagline (106 / 120 chars):** `Verify less, prove it: offline statutory citation checker with explicit abstention and signed commitments.`
- **Track:** `All BUIDLs` (Axes: `LegalTech & RegTech` · `AI × Blockchain`)
- **Tags:** `Bitcoin`, `Ethereum`
- **Repository URL:** `https://github.com/Grizaceo/dike` *(Private repository — access granted on request)*
  - **Why access is on request:** Diké's standalone engine and the `chile-base` statutory snapshot (derived from Biblioteca del Congreso Nacional de Chile under Ley Chile public-source attribution terms) are maintained in a private GitHub repository (`https://github.com/Grizaceo/dike`) to keep distribution controlled during the hackathon evaluation window while preserving a clean, auditable commit history separated from internal operational workspaces. Judges are granted read access immediately upon request, and every command below runs 100% offline (`--network none`) from the cloned repository.

---

## Description (≤ 400 words)

Legal AI tools routinely fail by over-claiming: they hallucinate statutes, guess missing code names, or certify citations they never checked. **Diké** is built on the opposite thesis—**verify less, prove it**:

1. **Explicit Abstention Over Guessing:** `dike constancia` checks every pinpoint statutory citation in a legal brief against a local, content-addressed corpus snapshot (`pack_hash` `fe458d6b9c57a8d7`: 25 Chilean statutes, 8,544 articles derived from Ley Chile / BCN). In the included synthetic brief (`docs/hackathon/escrito_demo.md`, 6 citations), Diké verifies 4 citations (`cl.norma.ct:art:0161`, `0162`, `0163`, `0168`) and explicitly refuses to certify 2: *artículo 60* (`AMBIGUOUS`: no statute named) and *artículo 9999 del Código del Trabajo* (`UNRESOLVABLE`: absent from corpus), exiting with code `1`.
2. **Privacy-Preserving Signed Commitment:** With `--emit-commitment DIR --sign`, Diké emits `commitment.json` and `commitment.sig.json`. The commitment uses a closed schema: it publishes only the verified provisions (canonical ID, source text SHA-256, in-force status, BCN source URL), `pack_hash`, reference dates, and citation counts (`total_citas: 6`, `citas_verificadas: 4`, `citas_fallidas: 2`). It omits brief prose, file paths, unverified citations, and the brief's SHA-256. The envelope binds the role (`content-integrity`), algorithm (`ed25519`), and contract (`dike-content-signature-v2`) inside the signed payload (`sha256("content-integrity:ed25519:dike-content-signature-v2:" + commitment_hash)`).
3. **Zero-Trust Verification Without Python:** A third party can verify the published commitment (`commitment_hash` `65f3ebe1da74d81ca59566f2ffe4b942ed6db1c2d2ecb891774da3f21b74522a`, `key_id` `3c7b3fde075efbe3`) completely offline without importing Diké—either via an independent Python verifier (`verificar_tercero.py`) or with zero Python using `jq`, GNU coreutils (`sha256sum`, `basenc`), and OpenSSL 3.

*(Note: All CLI outputs and commitment field names are in Spanish; `README.md` and `docs/hackathon/KEYS.md` provide English entry points.)*

---

## How to verify in 5 minutes

### 1. Run the offline end-to-end demo and test suite (Docker, network disabled)

```bash
git clone https://github.com/Grizaceo/dike
cd dike
docker build -t dike .
docker run --rm --network none dike
docker run --rm --network none dike python -m pytest -q
```

- `docker run --rm --network none dike` runs `docs/hackathon/demo_bli_e2e.py`: checks the 6-citation brief against the local corpus, signs a fresh commitment with a throwaway key, verifies it via both independent verifiers, proves tampering (`citas_verificadas` `4 -> 6`) fails with `exit 1`, and ends on the explicit refusal (`AMBIGUOUS` and `UNRESOLVABLE`).
- `docker run --rm --network none dike python -m pytest -q` runs the exported test suite offline (including literal execution of every bash block in `docs/hackathon/KEYS.md`).

### 2. Verify the published signed commitment without Diké's code

**Path 1 — Standalone Python (`stdlib` + `cryptography`, zero Diké imports):**

```bash
cd docs/hackathon
python3 verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub
```

Expected output ends with `RESULTADO: VERIFICADO` (exit `0`) and prints `key_id` `3c7b3fde075efbe3`.

**Path 2 — No Python (`jq` + GNU coreutils + OpenSSL 3 on Linux):**

Run the literal shell block under *Camino 2: sin Python, con jq, coreutils y OpenSSL* in `docs/hackathon/KEYS.md`:

```bash
cd docs/hackathon
(
set -euo pipefail
C=commitment.json; S=commitment.sig.json; K=content-signing-key.pub
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
for f in "$C" "$S"; do
  [ "$(tr -d '\000' < "$f" | wc -c)" -eq "$(wc -c < "$f")" ] || { echo "FALLA: $f trae bytes nulos"; exit 2; }
  jq -es 'length==1 and (.[0]|type=="object")' "$f" >/dev/null || { echo "FALLA: $f no es un único objeto JSON"; exit 2; }
  [ "$(jq -c --stream 'select(length==2)' "$f" | sort)" = "$(jq -c 'tostream|select(length==2)' "$f" | sort)" ] || { echo "FALLA: claves duplicadas en $f"; exit 2; }
done
N=$(sed -E 's/"([^"\\]|\\.)*"//g' "$C" | grep -aoE '[-+.0-9A-Za-z]+' | grep -avcE '^(0|-?[1-9][0-9]{0,14}|true|false|null)$' || true)
[ "$N" = 0 ] || { echo "FALLA: el commitment trae un número que no es un entero simple"; exit 2; }
jq -e '(keys == ["algorithm","commitment_hash","key_id","role","schema_version","signature"])
  and (.key_id|test("\\A[0-9a-f]{16}\\z")) and (.commitment_hash|test("\\A[0-9a-f]{64}\\z"))
  and (.signature|test("\\A[0-9a-f]{128}\\z"))' "$S" >/dev/null || { echo "FALLA: el sobre no tiene exactamente los seis campos con su formato"; exit 2; }
jq -e '.schema_version=="dike-content-signature-v2" and .role=="content-integrity" and .algorithm=="ed25519"' "$S" >/dev/null || { echo "FALLA: schema_version, role o algorithm inesperados"; exit 1; }
H=$(jq -cSj . "$C" | sha256sum | cut -d' ' -f1)
jq -e --arg h "$H" '.commitment_hash==$h' "$S" >/dev/null || { echo "FALLA: el hash NO coincide"; exit 1; }
tr -d '\r' < "$K" | sed '$a\' > "$T/clave.pem"
openssl pkey -pubin -in "$K" -out "$T/canonica.pem" 2>/dev/null && [ "$(sha256sum < "$T/clave.pem")" = "$(sha256sum < "$T/canonica.pem")" ] || { echo "FALLA: $K no es una clave pública PEM en su forma canónica"; exit 2; }
KID=$(openssl pkey -pubin -in "$K" -outform DER | tail -c 32 | sha256sum | cut -c1-16)
jq -e --arg k "$KID" '.key_id==$k' "$S" >/dev/null || { echo "FALLA: la firma no es de esta clave"; exit 1; }
echo "key_id: $KID"
printf '%s' "content-integrity:ed25519:dike-content-signature-v2:$H" | sha256sum | cut -d' ' -f1 | tr -d '\n' > "$T/firmado.txt"
jq -rj '.signature|ascii_upcase' "$S" | basenc -d --base16 > "$T/firma.bin"
openssl pkeyutl -verify -pubin -inkey "$K" -rawin -in "$T/firmado.txt" -sigfile "$T/firma.bin"
)
```

Expected output: `key_id: 3c7b3fde075efbe3` and `Signature Verified Successfully` (exit `0`).

---

## What it does NOT claim

- **Not an accredited legal timestamp (Chilean Law 19.799, Art. 5 No. 2):** Under Chilean law, a private instrument's date has legal faith only when backed by an electronic timestamp from an accredited provider (*prestador acreditado* before the Subsecretaría de Economía). Neither this Ed25519 signature nor any blockchain anchor is an accredited timestamp; `fecha_constancia` comes from the signing machine's clock.
- **Does not prove signer identity:** The signature proves *that* the commitment was signed by `key_id` `3c7b3fde075efbe3` for role `content-integrity`, not *who* holds that key (no certification provider certificate under Law 19.799 Art. 2(b) and Art. 11).
- **Does not validate substantive legal correctness:** Diké verifies that each cited article exists in the local corpus snapshot, has citable text (`texto_hash`), and is recorded as in force (`IN_FORCE`) on the reference date. It does **not** verify that the norm substantively supports the brief's legal argument—that judgment belongs to the lawyer, as declared inside `commitment.json` (`alcance` and `advertencias`).
- **Not today's live official text:** Verification runs offline against a dated BCN snapshot identified by `pack_hash` (`fe458d6b9c57a8d7`).

---

## Why it scales

The verification contract—a closed-schema canonical JSON `commitment`, a content-addressed statutory snapshot (`pack_hash`), explicit machine-readable abstention (`AMBIGUOUS` / `UNRESOLVABLE`), and a role-bound Ed25519 signature (`dike-content-signature-v2`) verifiable with standard OpenSSL—is completely independent of any single legal system. Chile (`chile-base`, 25 statutes, 8,544 articles) is the first corpus pack; any other jurisdiction whose consolidated legislation is packaged into the same manifest and article-hash format inherits the exact same offline verifier, zero-leakage commitment schema, and third-party auditability without changing a single line of the verification protocol.
