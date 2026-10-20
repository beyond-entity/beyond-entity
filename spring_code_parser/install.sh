#!/usr/bin/env bash
# Install be-parser from this unpacked release: copies lib/be-extractor.jar to <prefix>/lib and the launcher to
# <prefix>/bin. Not needed to run it: bin/be-parser works from here too.
# usage: ./install.sh [prefix]   (default prefix: ~/.local)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
prefix="${1:-$HOME/.local}"
mkdir -p "$prefix/bin" "$prefix/lib"
cp "$here/lib/be-extractor.jar" "$prefix/lib/be-extractor.jar"
cp "$here/bin/be-parser" "$prefix/bin/be-parser"
chmod +x "$prefix/bin/be-parser"
echo "installed: $prefix/bin/be-parser ($("$prefix/bin/be-parser" --version))"
case ":$PATH:" in
  *":$prefix/bin:"*) ;;
  *) echo "add to your shell profile:  export PATH=\"$prefix/bin:\$PATH\"" ;;
esac
