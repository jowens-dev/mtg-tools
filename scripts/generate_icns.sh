#!/bin/bash
set -e

# Path to the source image
SRC_IMAGE="../assets/app_icon.png"

# Directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -f "$SRC_IMAGE" ]; then
    echo "Error: Source image $SRC_IMAGE not found."
    exit 1
fi

ICONSET_DIR="../assets/app_icon.iconset"
mkdir -p "$ICONSET_DIR"

echo "Creating resized images for iconset..."
sips -s format png -z 16 16     "$SRC_IMAGE" --out "$ICONSET_DIR/icon_16x16.png" > /dev/null
sips -s format png -z 32 32     "$SRC_IMAGE" --out "$ICONSET_DIR/icon_16x16@2x.png" > /dev/null
sips -s format png -z 32 32     "$SRC_IMAGE" --out "$ICONSET_DIR/icon_32x32.png" > /dev/null
sips -s format png -z 64 64     "$SRC_IMAGE" --out "$ICONSET_DIR/icon_32x32@2x.png" > /dev/null
sips -s format png -z 128 128   "$SRC_IMAGE" --out "$ICONSET_DIR/icon_128x128.png" > /dev/null
sips -s format png -z 256 256   "$SRC_IMAGE" --out "$ICONSET_DIR/icon_128x128@2x.png" > /dev/null
sips -s format png -z 256 256   "$SRC_IMAGE" --out "$ICONSET_DIR/icon_256x256.png" > /dev/null
sips -s format png -z 512 512   "$SRC_IMAGE" --out "$ICONSET_DIR/icon_256x256@2x.png" > /dev/null
sips -s format png -z 512 512   "$SRC_IMAGE" --out "$ICONSET_DIR/icon_512x512.png" > /dev/null
sips -s format png -z 1024 1024 "$SRC_IMAGE" --out "$ICONSET_DIR/icon_512x512@2x.png" > /dev/null

echo "Converting iconset to icns..."
iconutil -c icns "$ICONSET_DIR"

echo "Cleaning up temporary iconset directory..."
rm -rf "$ICONSET_DIR"

echo "Successfully generated assets/app_icon.icns"
