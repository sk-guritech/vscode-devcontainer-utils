#!/bin/bash
#
# launcher.sh - Launch a new devcontainer from within an existing devcontainer
#
# This script converts a devcontainer path to its host equivalent and sends it
# to the devcontainer launcher server running on the host machine.
#
# Requirements:
#   - Docker CLI (to inspect container mounts)
#   - jq (for JSON parsing)
#   - Must be run from within a devcontainer
#   - Server must be running on host at port 9999
#

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder-path>" >&2
    echo "Example: $0 /workspaces/myproject" >&2
    exit 1
fi

# Get the directory path from argument
DIR_PATH="$1"

# Ensure the path is absolute and normalized
if [[ ! "$DIR_PATH" = /* ]]; then
    DIR_PATH="$(cd "$DIR_PATH" 2>/dev/null && pwd)" || DIR_PATH="$(pwd)/$DIR_PATH"
else
    # Normalize absolute path (resolve . and ..)
    DIR_PATH="$(cd "$DIR_PATH" 2>/dev/null && pwd)" || DIR_PATH="$DIR_PATH"
fi

# Use HOST_WORKSPACE_PATH environment variable if available
if [ -n "$HOST_WORKSPACE_PATH" ]; then
    # Replace /workspaces/server-agents-manager with HOST_WORKSPACE_PATH
    if [[ "$DIR_PATH" = /workspaces/server-agents-manager/* ]]; then
        RELATIVE_PATH="${DIR_PATH#/workspaces/server-agents-manager}"
        HOST_PATH="${HOST_WORKSPACE_PATH}${RELATIVE_PATH}"
    else
        echo "Error: Path $DIR_PATH is not within /workspaces/server-agents-manager" >&2
        exit 1
    fi
else
    echo "Error: HOST_WORKSPACE_PATH environment variable not set" >&2
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
