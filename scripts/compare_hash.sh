#!/bin/bash

# Verifiy args
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 file1 file2"
    exit 1
fi

file1="$1"
file2="$2"

# Verify files
if [ ! -f "$file1" ]; then
    echo "Error: $file1 does not exist."
    exit 1
fi

if [ ! -f "$file2" ]; then
    echo "Error: $file2 does not exist."
    exit 1
fi

# Verify if md5sum is installed
if ! command -v md5sum &> /dev/null; then
    echo "Error: md5sum is not installed. Please install it using 'sudo apt install -y ucommon-utils'."
    exit 1
fi

# Calculate the md5sum of each file
hash1=$(md5sum "$file1" | awk '{print $1}')
hash2=$(md5sum "$file2" | awk '{print $1}')

# Compare the hashes
if [ "$hash1" == "$hash2" ]; then
    echo "✅ The files are identical.."
else
    echo "❌ The files are not identical."
fi
