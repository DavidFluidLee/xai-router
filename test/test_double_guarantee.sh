#!/bin/bash

echo "🧪 开始双重保证测试..."

# 1. 直接添加
echo "1. 通过直接API添加关键路由..."
curl -X POST http://localhost:8081/admin/routes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "critical-payment",
    "path": "/api/payment/process",
    "method": "POST",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "import json\nimport time\nprint(json.dumps({\"stage\": \"direct-api\", \"timestamp\": int(time.time())}))",
    "timeout": 5
  }' > /dev/null 2>&1

sleep 1
echo "✅ 直接添加完成"

# 2. 测试直接添加效果
echo "2. 测试直接添加效果..."
curl -X POST http://localhost:8080/api/payment/process

# 3. 事件广播
echo "3. 通过事件广播更新路由..."
curl -X POST http://localhost:8081/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "UPDATE", 
    "route_id": "critical-payment-update",
    "route_data": {
      "id": "critical-payment",
      "path": "/api/payment/process",
      "method": "POST", 
      "handler": "sandbox",
      "sandbox_type": "python",
      "code": "import json\nimport time\nprint(json.dumps({\"stage\": \"event-broadcast\", \"timestamp\": int(time.time())}))",
      "timeout": 5
    }
  }' > /dev/null 2>&1

sleep 2
echo "✅ 事件广播完成"

# 4. 测试事件更新效果
echo "4. 测试事件更新效果..."
curl -X POST http://localhost:8080/api/payment/process

echo "🎉 双重保证测试完成！"
