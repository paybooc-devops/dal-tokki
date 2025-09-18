#!/usr/bin/env bash

set -euo pipefail

mkdir -p data/image/origin
mkdir -p data/image/new
mkdir -p data/image/transparent
mkdir -p data/video/result

# 이미지 빌드 및 태깅
docker build -t dal-tokki-api:latest -f Dockerfile .

# 스웜 배포 (Compose 파일 경로 주의: 대소문자 일치)
REPLICAS=3 docker stack deploy --pull -c Docker-compose.yaml dal-tokki