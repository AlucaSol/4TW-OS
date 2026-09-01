#!/bin/bash
set -euo pipefail

BUILD_DIR='/home/jonbe/bcld-4thewords-build'
SOURCE_DIR='/mnt/c/Users/jonbe/Documents/AI projects/4TW-OS/bcld'

if [[ -e "${BUILD_DIR}" ]]; then
    echo 'BUILD_DIR_EXISTS'
    exit 2
fi

git --version
git clone --branch develop/ALPHA --single-branch \
    https://github.com/duonl/bcld.git "${BUILD_DIR}"
cd "${BUILD_DIR}"

git -C "${SOURCE_DIR}" diff --binary -- \
    config/BUILD.conf \
    config/bcld/bcld.cfg \
    config/qutebrowser/config.py \
    test/bcld.md5 \
    test/md5sum \
    | git apply

git submodule update --init --recursive
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
