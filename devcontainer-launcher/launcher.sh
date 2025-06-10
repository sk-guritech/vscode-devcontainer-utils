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

# Get all mounts for this container
MOUNTS=$(docker inspect $(hostname) 2>/dev/null | jq -r '.[] | .Mounts[] | "\(.Destination):\(.Source)"')
if [ $? -ne 0 ]; then
    echo "Error: Failed to get container mount information" >&2
    exit 1
fi

# Find the mount that contains our directory
HOST_PATH=""
while IFS=: read -r dest src; do
    # Check if the directory path starts with this mount destination
    if [[ "$DIR_PATH" = "$dest"* ]]; then
        # Replace the destination path with source path
        RELATIVE_PATH="${DIR_PATH#$dest}"
        
        # Convert Unix path separators to Windows if source is Windows path
        if [[ "$src" =~ ^[a-zA-Z]:\\ ]]; then
            # Windows path detected, convert forward slashes to backslashes
            RELATIVE_PATH="${RELATIVE_PATH//\//\\}"
        fi
        
        HOST_PATH="${src}${RELATIVE_PATH}"
        break
    fi
done <<< "$MOUNTS"

# Check if we found a matching mount
if [ -z "$HOST_PATH" ]; then
    echo "Error: No mount found for $DIR_PATH" >&2
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