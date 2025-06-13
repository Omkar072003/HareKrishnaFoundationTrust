#!/bin/bash

# Define paths
ZIP_FILE="HareKrishna.zip"
DEST_DIR="harekrishna_extracted"

# Unzip the file
echo "Unzipping $ZIP_FILE..."
unzip "$ZIP_FILE" -d "$DEST_DIR"

# Optional: list the files
echo "Files extracted to $DEST_DIR:"
ls "$DEST_DIR"
