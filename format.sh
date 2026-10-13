#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

command -v python >/dev/null || {
	echo "python is required" >&2
	exit 1
}

if command -v ruff >/dev/null; then
	ruff format server
	ruff check server --fix
else
	echo "ruff is not installed; run: python -m pip install -r server/requirements-dev.txt" >&2
	exit 1
fi

if command -v djlint >/dev/null; then
	djlint --reformat --profile=jinja server/app/templates
else
	echo "djlint is not installed; run: python -m pip install -r server/requirements-dev.txt" >&2
	exit 1
fi

if command -v npx >/dev/null; then
	npx --yes prettier --write \
		"server/app/static/js/**/*.js" \
		"server/app/static/css/**/*.css" \
		"server/app/static/assets/*.svg" \
		"*.json"
fi

if command -v gradle >/dev/null; then
	gradle -p AdminApp spotlessApply
fi

echo "Formatted Python, Jinja templates, web assets, and Android Java where the required tools are installed."
