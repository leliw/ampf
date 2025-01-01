# AMPF - Angular + Material + Python + FastAPI

Remove previous built and build library again.

```bash
rm dist/*
python -m build
```

Upload to private repository.

```bash
python3 -m twine upload --repository-url https://europe-west3-python.pkg.dev/development-428212/pip dist/*
```
