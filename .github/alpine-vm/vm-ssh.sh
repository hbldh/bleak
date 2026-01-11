#!/usr/bin/env bash
# SSH wrapper for Alpine VM - executes commands in the VM

set -euo pipefail

# Execute command or open interactive shell
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR \
    -p 2222 \
    builder@localhost \
    "sh -l -c 'cd ~/repo && $*'"
