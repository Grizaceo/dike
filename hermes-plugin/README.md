# Diké for Hermes — native community plugin

Thin adapter over the unchanged Diké citation verifier. Not affiliated with or endorsed by Nous Research. Not admitted to the Hermes catalog yet.

## Surface

- Agent tool: `dike_verificar_citas`, with exactly one of `texto` or `ruta`.
- Manual command: `/dike-verificar <pasted text>` (does not collide with the `/dike` reasoning facade).
- The result preserves citation evidence and disclosure, but removes local filesystem locators. `mensaje` and `alcance` are scoped adapter explanations; `mensaje_motor` and `alcance_motor` identify original engine expressions, not broader guarantees.
- `todas_citas_detectadas_verificadas` covers only detected article citations. `todo_verificado` is false whenever unverified mentions remain. The detector can report a noisy standalone “Código”; it is surfaced rather than silently discarded.
- `SIN_CITAS` and `SIN_CORPUS` are valid abstentions, never positive verification. `no_verificadas` is exposed at top level. `evidencia_temporal` lists each verified source's retrieval date and age in calendar days. Both `certificacion_sustantiva` and `certificacion_vigencia_actual` are false.

Checks citation identity, source text integrity and temporal evidence against a local corpus; **does not certify legal interpretation or substantive support**. An unresolved reference is not proof that a norm does not exist. Always report corpus and reference date.

## Build and validation

From the repository root:

```sh
python scripts/generar_hermes_plugin.py
python scripts/generar_hermes_plugin.py --check
hermes plugins validate hermes-plugin --install-deps
PYTHONDONTWRITEBYTECODE=1 python -m pytest hermes-plugin/tests -q --confcutdir=hermes-plugin -p no:cacheprovider --basetemp="$TMPDIR/dike-plugin-tests"
```

Set TMPDIR to a managed scratch directory before testing. The test command isolates this plugin from root conftest side effects. The generated `motor/` and `corpus/` are byte-identical to their source files. The engine is not imported into Hermes. Dependencies have upper bounds. Linux, Python >=3.12 (tar extraction filter), Hermes >=0.21.5 is declared; minimum-version compatibility, Python versions other than the tested runtime, and other operating systems require separate verification.

Once the public release exists, install `<owner>/dike/hermes-plugin --ref <full commit SHA>` with `hermes plugins install`, then enable `dike`. Do not treat these placeholders as existing publication.

## Risk disclosures

Runs a finite-timeout Python subprocess with a minimal environment, stripped of agent credentials. Reads a user-specified regular `.md` or `.txt` file; refuses symlink paths and accepts at most 400000 UTF-8 bytes, also for pasted text. No network is needed by the verifier after plugin dependencies are installed. Dependency installation may access package registries.

Corpus installation and caches live under the current profile's `plugin-data/dike`; HOME is redirected there, not to the operator's home. The adapter writes temporary documents, installs persistent corpus data and permits engine caches. **Do not invoke it if the user prohibits these writes.** This does not imply Hermes itself has a zero-write mode.

First call installs the corpus and is slower; warm calls also rehash installed data and may take tens of seconds. Corpus package checksum is checked even when installed; installed files are checked against a generation manifest. Installation is locked and published by directory rename. A failed staging install is not reused. After an integrity error, stop calls, preserve affected data for diagnosis, and have the operator move the affected generation outside the generation directory before reinstalling from the trusted packaged corpus. Do not silently overwrite corrupted evidence. Abrupt termination can leave staging data; cleanup and old-generation retention remain manual. Moving the profile can invalidate absolute snapshot locators.

**This is not an OS sandbox.** The subprocess retains the user's OS permissions. Site-package directories from Hermes' active process are passed in PYTHONPATH because its interpreter may otherwise lack dependencies. This is a runtime compatibility seam, not a documented independent interpreter API.

Never signs, accesses signing keys, writes NIF, promotes graph knowledge or calls Hermes recursively. Manual invocation and model discovery are separate acceptance gates. A scripted model validates wiring only; autonomous use with a real model remains a separate measurement.

## License

The adapter and engine code are licensed under the [MIT License](../LICENSE). The statutory corpus snapshot under `corpus/` is derived from Ley Chile (Biblioteca del Congreso Nacional de Chile) and is subject to the provenance and public-source conditions documented in [`../corpus/README.md`](../corpus/README.md).
