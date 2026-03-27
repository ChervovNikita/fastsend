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

UV_BIN="$(command -v uv || true)"

if [[ -z "$UV_BIN" ]] && [[ -x "$HOME/.local/bin/uv" ]]; then
  UV_BIN="$HOME/.local/bin/uv"
fi

if [[ -z "$UV_BIN" ]]; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    UV_BIN="$HOME/.local/bin/uv"
  else
    UV_BIN="$(command -v uv || true)"
  fi
fi

echo "Installing fastsend into project venv..."
cd "$DIR"
if [[ -n "$UV_BIN" ]]; then
  if ! "$UV_BIN" sync; then
    echo "uv sync failed, falling back to pip..."
    UV_BIN=""
  fi
fi

if [[ -z "$UV_BIN" ]]; then
  echo "uv not available, falling back to pip..."
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  if [[ -z "$PYTHON_BIN" ]]; then
    echo "python3/python is required to install fastsend."
    exit 1
  fi

  "$PYTHON_BIN" -m venv "$DIR/.venv"
  "$DIR/.venv/bin/pip" install --upgrade pip
  "$DIR/.venv/bin/pip" install requests tqdm
fi

cat > "$BIN/fastsend" <<EOF
#!/usr/bin/env bash
exec "$DIR/.venv/bin/python" "$DIR/fastsend.py" "\$@"
EOF
chmod +x "$BIN/fastsend"

echo
echo "fastsend installed to $BIN/fastsend"
echo

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

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo "Open a new shell (or run: source \"$PROFILE\") to use fastsend."
  echo
fi
