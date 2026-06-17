---
name: pixi
description: Initialize, manage, and run Python environments using Pixi instead of pip, venv, conda, or poetry
---

# Pixi Python Management

Use this skill whenever working with Python environments, dependencies, or commands in a repository that uses (or should use) Pixi.

## Usage

Use this skill when:
- The project needs a Python environment
- Dependencies must be added, removed, or updated
- Running Python scripts, tests, or tooling
- Migrating from pip, poetry, or conda
- Pixi is present but not being used correctly

Do NOT use this skill when:
- The user explicitly asks to use another environment manager
- The task is unrelated to Python

## Steps

### 1. Detect Pixi setup

- Check for:
  - `pixi.toml`
  - `pyproject.toml` with `[tool.pixi]`
  - `pixi.lock`

If Pixi is not initialized:
pixi init
pixi add python

---

### 2. Add or update dependencies

Prefer Conda-forge:
pixi add <package>

Fallback to PyPI:
pixi add --pypi <package>

For dev tools:
pixi add --feature dev pytest ruff black

---

### 3. Run commands

Always execute via Pixi:

pixi run <command>

Examples:
pixi run python main.py
pixi run pytest
pixi run ruff check .

---

### 4. Create reusable tasks (if repeated)

pixi task add test "pytest"
pixi task add lint "ruff check ."

---

### 5. Update environment

pixi update

---

### 6. Migration handling (if needed)

From requirements.txt:
pixi add --pypi -r requirements.txt

From poetry:
- Read dependencies from `pyproject.toml`
- Re-add using:
pixi add --pypi <packages>

From conda:
pixi add <packages>

---

### 7. Validate environment

pixi info
pixi list

---

## Rules to Follow

- Never use:
  - pip install
  - python -m venv
  - conda
  - poetry
  - uv

- Never run Python directly:
  - Always use pixi run

- Never manually edit lockfiles

---

## When to Ask the User

Ask before:
- Changing Python version
- Large dependency changes
- Complex migrations

---

## Expected Outcome

- A working Pixi-managed Python environment
- Dependencies declared in Pixi config
- Commands executed via pixi run
- Reproducible environment via lockfile