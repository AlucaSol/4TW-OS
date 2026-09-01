#!/bin/bash
set -euo pipefail

cd /home/jonbe/bcld-4thewords-build
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y $(cat config/packages/BUILD)
apt-get install -y sbsigntool
