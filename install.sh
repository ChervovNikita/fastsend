#!/usr/bin/env bash
set -e

REPO="https://raw.githubusercontent.com/nickulrich/fastsend/main"
DIR="$HOME/.fastsend"
BIN="$HOME/.local/bin"

mkdir -p "$DIR"
mkdir -p "$BIN"

echo "Downloading fastsend..."
curl -fsSL "$REPO/fastsend.py"     -o "$DIR/fastsend.py"
curl -fsSL "$REPO/pyproject.toml"  -o "$DIR/pyproject.toml"

chmod +x "$DIR/fastsend.py"

if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "Installing dependencies..."
uv pip install --system requests tqdm

ln -sf "$DIR/fastsend.py" "$BIN/fastsend"

echo
echo "fastsend installed to $BIN/fastsend"
echo

if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
  echo "Add this to your shell profile:"
  echo
  echo '  export PATH="$HOME/.local/bin:$PATH"'
  echo
fi
