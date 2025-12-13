#!/bin/bash

# Flash AI Coding Agent - Docker Compose 중지 스크립트 (Linux/Mac)

echo ""
echo "[중지] Docker Compose 중지 중..."
docker-compose down

if [ $? -ne 0 ]; then
    echo "[에러] Docker Compose 중지에 실패했습니다."
    exit 1
fi

echo "[완료] 모든 서비스가 중지되었습니다."
echo ""
