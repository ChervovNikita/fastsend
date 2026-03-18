#!/usr/bin/env bash
set -e

REPO="https://raw.githubusercontent.com/ChervovNikita/fastsend/main"
DIR="$HOME/.fastsend"
BIN="$HOME/.local/bin"

mkdir -p "$DIR"
mkdir -p "$BIN"

echo "Downloading fastsend..."
curl -fsSL "$REPO/fastsend.py"    -o "$DIR/fastsend.py"
curl -fsSL "$REPO/pyproject.toml" -o "$DIR/pyproject.toml"
curl -fsSL "$REPO/uv.lock"        -o "$DIR/uv.lock" || true

if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "Installing fastsend into project venv..."
cd "$DIR"
uv sync

ln -sf "$DIR/.venv/bin/fastsend" "$BIN/fastsend"

echo
echo "fastsend installed to $BIN/fastsend"
echo

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo "Add this to your shell profile:"
  echo
  echo '  export PATH="$HOME/.local/bin:$PATH"'
  echo
fi
