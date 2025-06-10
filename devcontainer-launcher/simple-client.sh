#!/bin/bash
exec 3<>/dev/tcp/host.docker.internal/9999
echo "$1" >&3
cat <&3
exec 3<&-