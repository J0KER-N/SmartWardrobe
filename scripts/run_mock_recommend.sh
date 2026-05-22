#!/usr/bin/env bash
# 简单脚本：调用 internal mock recommend endpoint
API=${API_BASE:-http://127.0.0.1:8000}
echo "Calling mock recommend at $API/internal/mock_recommend"
curl -s -X POST "$API/internal/mock_recommend" -H "Content-Type: application/json" -d '{"n":3}' | jq
