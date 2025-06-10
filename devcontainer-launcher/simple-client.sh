#!/bin/bash

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder-path>"
    echo "Example: $0 /workspaces/myproject"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GET_HOST_PATH_SCRIPT="$SCRIPT_DIR/../get-host-path.sh"

# Check if get-host-path.sh exists
if [ ! -f "$GET_HOST_PATH_SCRIPT" ]; then
    echo "Error: get-host-path.sh not found at $GET_HOST_PATH_SCRIPT"
    exit 1
fi

# Convert folder path to host path
HOST_PATH=$("$GET_HOST_PATH_SCRIPT" "$1")
if [ $? -ne 0 ]; then
    echo "Error: Failed to get host path for $1"
    exit 1
fi

echo "Sending host path: $HOST_PATH"

# Send to server
exec 3<>/dev/tcp/host.docker.internal/9999
echo "$HOST_PATH" >&3
cat <&3
exec 3<&-