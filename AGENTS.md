# Codex instructions

This is the public TruLayer Python demos repo. `CLAUDE.md` is the detailed source of truth; read it before making any non-trivial change.

## Scope

- Runnable Python examples for the TruLayer SDK.
- Public customer-facing repo. Do not expose private service names, repo paths, planning issues, or private architecture.

## Working rules

- Make changes on a feature/fix branch and open a PR to `main`. Never commit directly to `main`.
- Keep examples focused: one SDK concept per file.
- Every example should run offline in CI with `TRULAYER_DRY_RUN=true`.
- Keep examples aligned with the SDK and docs.

## Verification

Run before opening a PR:

```bash
uv run pytest tests/
```

For changed examples, also run the example directly, for example:

```bash
uv run python examples/basic_trace.py
```
