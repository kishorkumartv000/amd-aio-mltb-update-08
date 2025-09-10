#!/bin/bash
# Apple Music Downloader - Resilient Version with Go Fallback + Path Control + Binary Execution Option
set -e

# Configuration
USE_FALLBACK=false          # true = use original fallback logic
USE_CUSTOM_GO=false         # true = force custom Go path only
USE_SYSTEM_GO=false          # true = force system Go path only
USE_BINARY_EXECUTION=true   # ✅ set to true to use compiled binary
CUSTOM_BINARY_NAME=am_downloader  # name of the compiled binary

# Fallback paths
CUSTOM_GO_BIN="$HOME/go-sdk/go/bin"
SYSTEM_GO_BIN="/usr/local/go/bin"

# If we are using the binary → skip Go setup
if [ "$USE_BINARY_EXECUTION" = true ]; then
    cmd=(
        /usr/local/bin/$CUSTOM_BINARY_NAME
        "$@"
    )
    echo "🚀 Executing via compiled binary: $CUSTOM_BINARY_NAME"
else
    # Select Go path (only needed for go run)
    if [ "$USE_FALLBACK" = true ]; then
        if [ -x "$CUSTOM_GO_BIN/go" ]; then
            export PATH="$PATH:$CUSTOM_GO_BIN"
            echo "Using Go from custom path (fallback): $CUSTOM_GO_BIN"
        elif [ -x "$SYSTEM_GO_BIN/go" ]; then
            export PATH="$PATH:$SYSTEM_GO_BIN"
            echo "Using Go from system path (fallback): $SYSTEM_GO_BIN"
        elif command -v go >/dev/null 2>&1; then
            echo "Using Go from system environment: $(command -v go)"
        else
            echo "❌ Go compiler not found in custom or system paths."
            exit 1
        fi
    else
        if [ "$USE_CUSTOM_GO" = true ] && [ -x "$CUSTOM_GO_BIN/go" ]; then
            export PATH="$PATH:$CUSTOM_GO_BIN"
            echo "Using Go from custom path (forced): $CUSTOM_GO_BIN"
        elif [ "$USE_SYSTEM_GO" = true ] && [ -x "$SYSTEM_GO_BIN/go" ]; then
            export PATH="$PATH:$SYSTEM_GO_BIN"
            echo "Using Go from system path (forced): $SYSTEM_GO_BIN"
        else
            echo "❌ Go compiler not found or no path selected."
            exit 1
        fi
    fi

    # 🛠️ For go run, must cd into project dir
    cd "$HOME/amalac"
    cmd=(
        go run main.go
        "$@"
    )
    echo "Executing via Go source: main.go"
fi

# Execute download
echo "Starting Apple Music download..."
"${cmd[@]}"

# Output success message
echo "✅ Download completed successfully!"
