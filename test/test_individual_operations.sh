#!/bin/bash

# 单独操作测试脚本
# 用于快速测试特定功能

MANAGEMENT_URL="http://localhost:8081/admin"
GATEWAY_URL="http://localhost:8080"

case $1 in
    "health")
        echo "🔍 健康检查:"
        curl -s "$MANAGEMENT_URL/health" | jq .
        ;;
    "routes")
        echo "📋 所有路由:"
        curl -s "$MANAGEMENT_URL/routes" | jq .
        ;;
    "sandboxes") 
        echo "🖥️  所有沙箱:"
        curl -s "$MANAGEMENT_URL/sandboxes" | jq .
        ;;
    "create")
        echo "➕ 创建测试路由:"
        curl -X POST "$MANAGEMENT_URL/routes" \
          -H "Content-Type: application/json" \
          -d '{
            "id": "quick-test",
            "path": "/quick/test",
            "method": "GET", 
            "handler": "sandbox",
            "sandbox_type": "python",
            "code": "import json\nprint(json.dumps({\"quick\": \"test\", \"timestamp\": \"'$(date +%s)'\"}))",
            "timeout": 5
          }'
        ;;
    "test")
        echo "⚡ 测试路由执行:"
        curl -s "$GATEWAY_URL/quick/test"
        ;;
    "update")
        echo "✏️  更新路由:"
        curl -X PUT "$MANAGEMENT_URL/routes/quick-test" \
          -H "Content-Type: application/json" \
          -d '{
            "id": "quick-test",
            "path": "/quick/test",
            "method": "GET",
            "handler": "sandbox",
            "sandbox_type": "python",
            "code": "import json\nprint(json.dumps({\"quick\": \"test\", \"updated\": true, \"timestamp\": \"'$(date +%s)'\"}))",
            "timeout": 5
          }'
        ;;
    "delete")
        echo "🗑️  删除路由:"
        curl -X DELETE "$MANAGEMENT_URL/routes/quick-test"
        ;;
    "load")
        echo "📊 负载测试:"
        for i in {1..3}; do
            echo "请求 $i:"
            curl -s "$GATEWAY_URL/execute"
            echo ""
        done
        echo "沙箱负载:"
        curl -s "$MANAGEMENT_URL/sandboxes" | jq '.sandboxes[] | {id: .id, load: .load}'
        ;;
    *)
        echo "用法: $0 [health|routes|sandboxes|create|test|update|delete|load]"
        echo "示例:"
        echo "  $0 health        # 检查健康状态"
        echo "  $0 create        # 创建测试路由" 
        echo "  $0 test          # 测试路由"
        echo "  $0 update        # 更新路由"
        echo "  $0 delete        # 删除路由"
        echo "  $0 load          # 负载测试"
        ;;
esac
