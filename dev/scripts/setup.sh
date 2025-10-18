#!/bin/bash
# Proxy to original scripts/setup.sh to keep history
set -e
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
"$DIR/../setup.sh" "$@"
