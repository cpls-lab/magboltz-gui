# Packaging & PyPI Upload

This project uses standard PEP 517/518 packaging. The script below builds the sdist and wheel.

## Build

```bash
bash scripts/build_package.sh
```

Outputs:
- `dist/*.tar.gz` (sdist)
- `dist/*.whl` (wheel)

## Verify

```bash
python3 -m twine check dist/*
```

## Upload (TestPyPI)

```bash
python3 -m twine upload --repository testpypi dist/*
```

## Upload (PyPI)

```bash
python3 -m twine upload dist/*
```

## Notes

- Use API tokens for Twine (`~/.pypirc` or `TWINE_PASSWORD`).
- If you change version, rebuild before uploading.
