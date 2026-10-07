# Diké for Hermes — native community plugin

Thin adapter over the unchanged Diké citation verifier. Not affiliated with or endorsed by Nous Research. Not admitted to the Hermes catalog yet. Code licensing and corpus redistribution review remain pending; this is not a public release.

## Surface

- Agent tool: `dike_verificar_citas`, with exactly one of `texto` or `ruta`.
- Manual command: `/dike-verificar <pasted text>` (does not collide with the `/dike` reasoning facade).
- The result preserves the engine's `detalles`, `problemas`, `meta`, `citation_disclosure` and `alcance`. It adds `todo_verificado` and `certificacion_sustantiva: false`.

Checks citation identity, source text integrity and temporal evidence against a local corpus; **does not certify legal interpretation or substantive support**. An unresolved reference is not proof that a norm does not exist. Always report corpus and reference date.

## Build and validation

From the repository root:

```sh
python scripts/generar_hermes_plugin.py
python scripts/generar_hermes_plugin.py --check
hermes plugins validate hermes-plugin --install-deps
python -m pytest hermes-plugin/tests -q
```

The generated `motor/` and `corpus/` are byte-identical to their source files. The engine is not imported into Hermes. Dependencies have upper bounds. Linux, Python >=3.12 (tar extraction filter), Hermes >=0.21.5; other operating systems are untested.

Once the public release exists, install `<owner>/dike/hermes-plugin --ref <full commit SHA>` with `hermes plugins install`, then enable `dike`. Do not treat these placeholders as existing publication.

## Risk disclosures

Runs a finite-timeout Python subprocess with a minimal environment, stripped of agent credentials. Reads a user-specified regular `.md` or `.txt` file; refuses symlink paths and accepts at most 400000 UTF-8 bytes, also for pasted text. No network is needed by the verifier after plugin dependencies are installed. Dependency installation may access package registries.

Corpus installation and caches live under the current profile's `plugin-data/dike`; HOME is redirected there, not to the operator's home. First call installs the corpus and is slower. Corpus package checksum is checked even when installed; installed files are checked against a generation manifest. Installation is locked and published by directory rename. A failed staging install is not reused; integrity failures require explicit repair, not silent replacement.

**This is not an OS sandbox.** The subprocess retains the user's OS permissions. Site-package directories from Hermes' active process are passed in PYTHONPATH because its interpreter may otherwise lack dependencies. This is a runtime compatibility seam, not a documented independent interpreter API.

Never signs, accesses signing keys, writes NIF, promotes graph knowledge or calls Hermes recursively. Manual invocation and model discovery are separate acceptance gates. A scripted model validates wiring only; autonomous use with a real model remains a separate measurement.

## License

Not yet selected by the owner. Do not infer MIT or another license from this adapter. Corpus attribution and redistribution terms require separate legal review.
