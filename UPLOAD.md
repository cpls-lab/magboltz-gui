uv pip install build twine
uv run python3 -m build

uv run python3 -m twine upload dist/*
