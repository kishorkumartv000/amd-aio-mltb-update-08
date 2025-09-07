#!/bin/bash
# Apple Music Downloader - Simplified Version
set -e

# Explicitly add Go to PATH
export PATH="$PATH:/usr/local/go/bin"

# Change to Go project directory
cd "$HOME/amalac"

# Build the download command
cmd=(
    go run main.go
    "$@"
)

# Execute download
echo "Starting Apple Music download..."
"${cmd[@]}"

# Output success message
echo "Download completed successfully!"
