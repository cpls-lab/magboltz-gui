# GUI Tests

This directory contains tests that exercise Qt widgets through `pytest-qt`.

Default CI keeps GUI tests out of the core path:

```bash
python -m pytest -q -m "not gui and not magboltz"
```

When Qt dependencies are available, GUI tests can be run explicitly:

```bash
pip install -e ".[test-gui]"
python -m pytest -q -m gui
```

Keep GUI tests thin. Core behaviour should live in non-GUI tests; GUI tests
should verify that widgets bind user actions to the tested core layer.
