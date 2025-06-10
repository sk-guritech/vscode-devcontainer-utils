#!/bin/bash
#
# devcontainer-path-to-host.sh
#
# Description:
#   Converts a path inside a devcontainer to its corresponding path on the host system.
#   This is useful when you need to reference host filesystem paths from within a devcontainer,
#   such as when launching other applications or sharing paths with host-based tools.
#
# Features:
#   - Automatically detects and handles Windows/Unix path separator differences
#   - Resolves relative paths to absolute paths
#   - Works with any mounted directory in the devcontainer
#
# Requirements:
#   - Docker CLI (to inspect container mounts)
#   - jq (for JSON parsing)
#   - Must be run from within a devcontainer
#
# Usage:
#   ./devcontainer-path-to-host.sh <directory-path>
#
# Examples:
#   ./devcontainer-path-to-host.sh /workspaces/myproject
#   ./devcontainer-path-to-host.sh .
#   ./devcontainer-path-to-host.sh ../other-project
#
# Output:
#   Prints the host system path corresponding to the given devcontainer path
#   Exit code 0 on success, 1 on error
#

# Check if argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory-path>"
    echo "Example: $0 /workspaces/manager"
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

# Find the mount that contains our directory
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
        echo "$HOST_PATH"
        exit 0
    fi
done <<< "$MOUNTS"

echo "Error: No mount found for $DIR_PATH"
exit 1