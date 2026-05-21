# Contributing

Self Atlas should stay useful, local-first, and emotionally precise. Please do not turn it into a generic productivity questionnaire with better branding. The world has suffered enough.

## Development

Run the test suite:

```bash
python3 tests/test_self_atlas.py
```

Run the public-release check:

```bash
python3 scripts/public_release_check.py
```

## Contribution rules

- Use fictional examples and fixture data only.
- Keep real vaults, raw captures, exports, and private names out of commits.
- Prefer small, reviewable changes.
- Preserve source evidence and confidence semantics.
- Do not add network sync, cloud upload, analytics, or telemetry without an explicit design and privacy discussion.
- Keep questions concrete: dates, scenes, names, artifacts, numbers, and links beat generic self-help mush.
