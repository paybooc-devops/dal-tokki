#!/usr/bin/env bash

set -euo pipefail

# 이미지 빌드 및 태깅
docker build -t tokki-video-jobs-api:latest -f Dockerfile .

# 스웜 배포 (Compose 파일 경로 주의: 대소문자 일치)
docker stack deploy -c Docker-compose.yaml dal-tokki