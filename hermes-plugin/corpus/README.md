# Corpus: `chile-base`

`chile-base-ea28fa1c0f9af6c1.tar.gz` is the corpus Diké verifies citations
against in this repository: 25 Chilean statutes, 8,544 articles, each with its
text hash, its source URL and its in-force window.

| | |
|---|---|
| `pack_hash` | `ea28fa1c0f9af6c1` — the first 16 hex digits of the SHA-256 of the unpacked tree. Every commitment carries it |
| Source | Ley Chile, Biblioteca del Congreso Nacional de Chile (`https://nuevo.leychile.cl/servicios/Navegar/get_norma_json`), one statute per request |
| Retrieved | 2026-08-18 (dataset version 2026-08-16), per the package's `MANIFEST.json` |
| Statutes | The 25 Ley Chile codes listed in `pack.json` (`includedLeychileCodes`); 207436 is the Código del Trabajo |
| Left out | 464 articles the builder excluded, counted in `BUILD_REPORT.json` |
| Checksum | `SHA256SUMS`, checked by the `Dockerfile` before installing |

## Install

```bash
tar -xzf chile-base-ea28fa1c0f9af6c1.tar.gz -C /tmp
dike starter --user demo install /tmp/chile-base --name chile-base
```

`dike starter install` validates the whole package (manifest, schema, and that
every article's `textSha256` matches its text) before sealing it. It does not
use the network.

## Terms the package declares

These are the package's own statements, in the `componentLicenses` and `aiUse`
fields of its `MANIFEST.json`. They were written by the author of the package
on the basis of BCN's *Condiciones de Uso API Ley Chile* (v1.0, which the
manifest says it checked on 2026-08-09). **They have not been re-checked for
this repository; read BCN's current terms before redistributing.**

- Legal texts: outside copyright per section 9 of those terms; attribution
  required — *Ley Chile – Biblioteca del Congreso Nacional*.
- Metadata: minimal factual data; BCN's ontology and compilation are not
  copied.
- Schema of the package: MIT, by the package's author.
- AI use: intended for lookup, retrieval and display. Training or fine-tuning
  models on the BCN-derived components requires BCN's express authorization.

## Limits

- **It is a dated copy.** It is not the official text of today, and a
  commitment only says a provision was in force according to this copy.
- **No public registry of `pack_hash` values** exists yet: a third party sees
  the identifier and has this file to match it against, nothing else.
- **Identifiers under `https://lexo.cl/…`.** The package uses that prefix for
  its `@id` values. They are names, not links, and the domain does not belong
  to this project.
