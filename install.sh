#!/usr/bin/env sh
set -e

echo "======================================="
echo " Installing Node.js, uv, and Ollama"
echo "======================================="
echo ""

# Detect OS
OS="$(uname -s)"

# ---- Helper: check if a command exists ----
has() {
    command -v "$1" >/dev/null 2>&1
}

# ---- Node.js ----
echo "[1/3] Installing Node.js (LTS)..."

if has node; then
    echo "  Node.js is already installed: $(node --version)"
elif [ "$OS" = "Darwin" ]; then
    if has brew; then
        brew install node@lts
    else
        echo "  Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install node@lts
    fi
elif [ "$OS" = "Linux" ]; then
    # Use NodeSource setup script for a current LTS release
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sh - 2>/dev/null || \
    curl -fsSL https://rpm.nodesource.com/setup_lts.x | sh - 2>/dev/null || true

    if has apt-get; then
        apt-get install -y nodejs
    elif has dnf; then
        dnf install -y nodejs
    elif has yum; then
        yum install -y nodejs
    else
        echo "  ERROR: No supported package manager found (apt, dnf, yum)."
        exit 1
    fi
else
    echo "  ERROR: Unsupported OS: $OS"
    exit 1
fi

echo "Node.js installed: $(node --version 2>/dev/null || echo 'restart terminal to verify')"
echo ""

# ---- uv ----
echo "[2/3] Installing uv..."

if has uv; then
    echo "  uv is already installed: $(uv --version)"
else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "  uv installed successfully."
fi
echo ""

# ---- Ollama ----
echo "[3/3] Installing Ollama..."

if has ollama; then
    echo "  Ollama is already installed: $(ollama --version)"
elif [ "$OS" = "Darwin" ]; then
    if has brew; then
        brew install --cask ollama
    else
        echo "  ERROR: Homebrew is required to install Ollama on macOS."
        exit 1
    fi
elif [ "$OS" = "Linux" ]; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "  ERROR: Unsupported OS: $OS"
    exit 1
fi

echo "Ollama installed: $(ollama --version 2>/dev/null || echo 'restart terminal to verify')"
echo ""

echo "======================================="
echo " All tools installed successfully!"
echo " Restart your terminal so that"
echo " PATH changes take effect."
echo "======================================="
