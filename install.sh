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
  PATH_EXPORT='export PATH="$HOME/.local/bin:$PATH"'

  case "${SHELL##*/}" in
    zsh) PROFILE="$HOME/.zshrc" ;;
    bash) PROFILE="$HOME/.bashrc" ;;
    *) PROFILE="$HOME/.profile" ;;
  esac

  touch "$PROFILE"
  if ! grep -Fxq "$PATH_EXPORT" "$PROFILE"; then
    echo "$PATH_EXPORT" >> "$PROFILE"
    echo "Added $BIN to PATH in $PROFILE"
  else
    echo "$BIN is already configured in $PROFILE"
  fi

  echo "Open a new shell (or run: source \"$PROFILE\") to use fastsend."
  echo
fi
