#!/bin/bash
#
# launcher.sh - Launch a new devcontainer from within an existing devcontainer
#
# This script converts a devcontainer path to its host equivalent and sends it
# to the devcontainer launcher server running on the host machine.
#

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder-path>" >&2
    echo "Example: $0 /workspaces/myproject" >&2
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GET_HOST_PATH_SCRIPT="$SCRIPT_DIR/../get-host-path.sh"

# Check if get-host-path.sh exists
if [ ! -f "$GET_HOST_PATH_SCRIPT" ]; then
    echo "Error: get-host-path.sh not found at $GET_HOST_PATH_SCRIPT" >&2
    exit 1
fi

# Convert folder path to host path
HOST_PATH=$("$GET_HOST_PATH_SCRIPT" "$1" 2>&1)
if [ $? -ne 0 ]; then
    echo "Error: Failed to get host path for $1" >&2
    exit 1
fi

# Send to server and capture response
if ! exec 3<>/dev/tcp/host.docker.internal/9999 2>/dev/null; then
    echo "Error: Cannot connect to server at host.docker.internal:9999" >&2
    exit 1
fi

echo "$HOST_PATH" >&3
RESPONSE=$(cat <&3)
exec 3<&-

# Check if response is an error
if [[ "$RESPONSE" =~ ^error: ]]; then
    echo "$RESPONSE" >&2
    exit 1
fi

# Output only the container ID
echo "$RESPONSE"