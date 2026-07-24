#!/usr/bin/env bash
# Copy .ai_agent/commands into .cursor/commands (flat) for Cursor slash-command discovery.
# Cursor does not reliably follow symlinks or scan subdirectories under .cursor/commands/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/.ai_agent/commands"
DEST="${ROOT}/.cursor/commands"

if [[ ! -d "$SRC" ]]; then
	echo "error: source directory not found: $SRC" >&2
	exit 1
fi

mkdir -p "${ROOT}/.cursor"

if [[ -L "$DEST" ]]; then
	rm "$DEST"
fi
mkdir -p "$DEST"

declare -A seen=()
while IFS= read -r -d '' file; do
	base="$(basename "$file")"
	if [[ -n "${seen[$base]:-}" ]]; then
		echo "error: duplicate command filename '$base' under $SRC" >&2
		exit 1
	fi
	seen[$base]=1
done < <(find "$SRC" -name '*.md' -type f -print0)

rm -f "${DEST}"/*.md 2>/dev/null || true

count=0
while IFS= read -r -d '' file; do
	cp "$file" "${DEST}/$(basename "$file")"
	count=$((count + 1))
done < <(find "$SRC" -name '*.md' -type f -print0)

echo "Synced ${count} command(s) from .ai_agent/commands to .cursor/commands"
