#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -x "$PWD/vendor/bin/pandoc" ]]; then export PATH="$PWD/vendor/bin:$PATH"; fi
exec /usr/bin/python3 -m donusturucu.app "$@"
