#!/usr/bin/env bash
# copy_2_pi.sh
# Copy all .py and project.toml files from the script's directory (recursively)
# to a remote destination (only argument is destination, e.g. pi@host:/path).

set -euo pipefail

usage() {
    echo "Usage: $0 <remote-destination>"
    echo "Example: $0 pi@192.168.1.42:/home/pi/project"
    exit 2
}

if [ "$#" -ne 1 ]; then
    usage
fi

DEST="$1"
# directory containing this script -> treated as source root
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# find files to copy
mapfile -d '' files < <(find "$SRC_DIR" -type f \( -name '*.py' -o -name '*.toml' \) -print0)

if [ "${#files[@]}" -eq 0 ]; then
    echo "No .py or project.toml files found under $SRC_DIR"
    exit 0
fi

# build a null-separated list and feed to rsync --files-from=-
# rsync will recreate the relative paths under DEST
printf '%s\0' "${files[@]#$SRC_DIR/}" | \
    rsync -av --from0 --files-from=- "$SRC_DIR/" "$DEST"

echo "Copied ${#files[@]} files to $DEST"
# filter out unwanted files (build/ dirs, *.egg files, any hidden directory component)
filtered=()
for f in "${files[@]}"; do
    rel=${f#"$SRC_DIR"/}
    # skip hidden dirs (any path component starting with a dot)
    case "$rel" in
        .*|*/.*) continue ;;
    esac
    # skip build directories and .egg files
    case "$rel" in
        *build|**/build|*.egg*) continue ;;
    esac
    filtered+=("$rel")
done

if [ "${#filtered[@]}" -eq 0 ]; then
    echo "No .py or pyproject.toml files left to copy after applying excludes"
    exit 0
fi

# copy only the filtered list
printf '%s\0' "${filtered[@]}" | \
    rsync -av --from0 --files-from=- "$SRC_DIR/" "$DEST"

echo "Copied ${#filtered[@]} files to $DEST (excluded build/, *.egg and hidden folders)"