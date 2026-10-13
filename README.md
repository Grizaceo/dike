# Diké

Diké checks every statutory citation in a Chilean legal brief against a local,
hash-identified copy of the law, and **refuses to certify what it cannot
prove**. For the citations it did verify it can emit a small signed
*commitment* that anyone can check offline, without Diké's code.

This repository is the citation-verification engine on its own: the command
line tool, a corpus of 25 Chilean statutes, a signed example and the kit to
verify it.

> Most of the documentation and all program output are in Spanish. This page
> is the English entry point.

## Run it

You need Docker. Nothing else from the author's machine is involved, and once
the image is built it runs with the network disabled.

```bash
docker build -t dike .
docker run --rm --network none dike
```

That runs the demo end to end on a synthetic brief with six citations:

1. `dike constancia` verifies four of them against the corpus;
2. it refuses the other two — *artículo 60* (no statute named: ambiguous) and
   *artículo 9999 del Código del Trabajo* (does not exist) — and says why;
3. it emits a commitment that lists only the four verified citations, signed
   with a throwaway key generated on the spot;
4. the signature is verified twice by code that is not Diké's: a standalone
   Python script, and a `jq` + OpenSSL recipe;
5. one number in the commitment is altered, and both verifications fail.

The demo ends on the refusal, not on the hash. That is the product.

Run the test suite the same way:

```bash
docker run --rm --network none dike python -m pytest -q
```

## Verify the published example yourself

`docs/hackathon/` holds a commitment signed with the project's real content
key, the public key, and two independent ways to check it. You do not need
this repository's code for either; `docs/hackathon/KEYS.md` (Spanish) has the
exact commands, what the signature proves and — at more length — what it does
not.

```bash
cd docs/hackathon
python3 verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub
```

Compare the `key_id` it prints with the one in `KEYS.md`: a public key that
travels next to a signature proves nothing by itself.

The example is reproducible. Inside the container, the same brief gives the
same commitment except for its two date fields (`as_of` and
`fecha_constancia`), which is all this prints:

```bash
docker run --rm --network none dike bash -c \
  'dike constancia docs/hackathon/escrito_demo.md --emit-commitment /tmp/c >/dev/null 2>&1; \
   diff <(python -m json.tool /tmp/c/commitment.json) <(python -m json.tool docs/hackathon/commitment.json)'
```

## What a commitment says, and what it does not

It says that each listed provision **exists in the corpus, has citable text
and was in force** on the reference date, and it names the corpus by
`pack_hash`. The signature shows the commitment was not altered after signing.

It does **not** say that the provision supports what the brief claims: that is
the lawyer's judgment, and the commitment says so in its own `alcance` and
`advertencias` fields. The signature does not prove who holds the key, and the
date has no legal value in Chile: Ley 19.799 requires a timestamp from an
accredited provider for that, and this is not one. `KEYS.md` states each limit
and points to the test behind every claim it makes.

## Use it without Docker

Linux, Python 3.11 or later.

```bash
pip install ./packages/dike-id/python
pip install -e ".[test]"

mkdir -p ~/.lexo && printf 'starter:\n  user: demo\n' > ~/.lexo/config.yaml
tar -xzf corpus/chile-base-ea28fa1c0f9af6c1.tar.gz -C /tmp
dike starter --user demo install /tmp/chile-base --name chile-base

dike constancia my-brief.md                    # exit 0: all verified; 1: some were not
dike constancia my-brief.md --json
```

To sign a commitment you need an Ed25519 content key, mode 0600, whose path
you pass in `LEXO_CONTENT_SIGNING_KEY_PATH`:

```bash
python -c "from lexo_cli.content_signing import generar_content_key as g; print(g('$HOME/.dike-keys/content-signing-key.pem'))"
LEXO_CONTENT_SIGNING_KEY_PATH=~/.dike-keys/content-signing-key.pem \
  dike constancia my-brief.md --emit-commitment out/ --sign
```

Briefs in `.docx` or `.pdf` need the optional extra: `pip install -e ".[documentos]"`.

## The corpus

`corpus/chile-base-ea28fa1c0f9af6c1.tar.gz` is a snapshot of 25 statutes
(8,544 articles) taken from Ley Chile, the public service of the Biblioteca
del Congreso Nacional de Chile. See `corpus/README.md` for its provenance,
the terms it declares, and its known limits. It is a dated copy, not the
official text of today: the `pack_hash` in every commitment says which copy.

## Layout

| Path | What it is |
|---|---|
| `lexo_cli/` | The engine. `commands/constancia.py` is the command; `commitment.py` and `content_signing.py` build and sign the commitment; `starter/` reads the corpus |
| `shared/`, `packages/dike-id/` | Schemas and the identifier grammar the engine depends on |
| `docs/hackathon/` | The verification kit (`KEYS.md`, `verificar_tercero.py`, the signed example), the demo and the signature log |
| `corpus/` | The corpus snapshot and its checksum |
| `lexo_cli/tests/` | Tests. `test_keys_md_ejecutable.py` runs the commands of `KEYS.md` literally |
| `scripts/hackathon/` | Tools that test the tests: a mutation battery, a random search for disagreements between the three verifiers, and a runner for other Linux distributions |

## Status and limits

- **Tested on Linux only.** The engine: on Arch, and in the Debian 13 image
  this repository builds (552 tests pass there, 3 are skipped and say why).
  The two verification paths of the kit: also on Debian 12 and Ubuntu 22.04
  and 24.04.
- **One command.** This distribution carries `dike constancia` and
  `dike starter`. Diké's other commands are not part of it.
- **Names are historical.** The Python package is called `lexo_cli`, the kit
  lives under `docs/hackathon/`, and the configuration file is
  `~/.lexo/config.yaml`.
- **Leftovers of the larger codebase.** Some modules still carry defaults that
  point to services this distribution does not include (a search index, an
  agent runtime). `dike constancia` does not use them.
- **Identifiers under `lexo.cl`.** The corpus format uses `https://lexo.cl/…`
  as identifier prefix. Those are names, not links, and that domain does not
  belong to this project.
- **License.** The code, schemas, and verification scripts in this repository
  are licensed under the [MIT License](LICENSE). The statutory snapshot under
  `corpus/` (and mirrored in `hermes-plugin/corpus/`) is governed by the
  official public-source conditions of the Biblioteca del Congreso Nacional de
  Chile (Ley Chile), as documented in [`corpus/README.md`](corpus/README.md).

## Where this code comes from

The files listed in `.origen.json` are exported from the author's private
development repository, at the commit that file names. Everything else here —
this page, the `Dockerfile`, `pyproject.toml`, `lexo_cli/main.py` — belongs to
this repository.
