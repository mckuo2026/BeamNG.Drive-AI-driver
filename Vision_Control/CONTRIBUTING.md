# Contributing

BeamNG and Horizon Driver is a Windows-first visual driving assistant.
Contributions should keep the project usable for cloud-computer players who
need low latency, clear UI, and simple setup.

## Local Setup

```bat
cd Vision_Control
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Quality Checks

Run these before opening a pull request:

```bat
pytest
ruff check src tests
python -m vision_control.main --selftest
```

## Coding Guidelines

- Keep user-facing project text in English unless it belongs to the UI
  translation table.
- Keep the default UI language English.
- Use small, focused modules for capture, perception, planning, control, and UI.
- Avoid CPU-heavy work in the UI thread.
- Keep drive output opt-in and release all controls on pause, stop, error, or
  process shutdown.

## Branches

- `main`: stable repository branch.
- `codex/*`: implementation branches created by Codex.
- `feature/*`: focused human-authored feature branches.

## Pull Request Checklist

- Tests pass.
- README or docs are updated for visible behavior changes.
- New UI strings are added to all languages in `src/vision_control/i18n.py`.
- Capture or control changes include a manual smoke-test note.
