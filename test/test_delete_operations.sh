#!/bin/bash

echo "🧪 测试删除操作同步..."
echo "=========================================="

# 1. 测试直接删除
echo "1. 测试直接删除..."
curl -X POST http://localhost:8081/admin/routes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "direct-delete-test",
    "path": "/api/direct-delete",
    "method": "GET",
    "handler": "sandbox", 
    "sandbox_type": "python",
    "code": "print(\"Direct delete test\")",
    "timeout": 5
  }' > /dev/null 2>&1

echo "创建的路由:"
curl -s http://localhost:8081/admin/routes | jq '.routes[] | select(.id == "direct-delete-test")'

echo "删除路由..."
curl -X DELETE http://localhost:8081/admin/routes/direct-delete-test

echo "删除后检查:"
curl -s http://localhost:8081/admin/routes | jq '.routes[] | select(.id == "direct-delete-test")'

# 2. 测试事件删除
echo "2. 测试事件删除..."
curl -X POST http://localhost:8081/admin/routes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "event-delete-test", 
    "path": "/api/event-delete",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "print(\"Event delete test\")",
    "timeout": 5
  }' > /dev/null 2>&1

echo "创建的路由:"
curl -s http://localhost:8081/admin/routes | jq '.routes[] | select(.id == "event-delete-test")'

echo "发布删除事件..."
curl -X POST http://localhost:8081/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "DELETE",
    "route_id": "event-delete-test"
  }' > /dev/null 2>&1

sleep 2

echo "事件删除后检查:"
curl -s http://localhost:8081/admin/routes | jq '.routes[] | select(.id == "event-delete-test")'

# 3. 检查事件流
echo "3. 事件流状态:"
curl -s http://localhost:8081/admin/events/stream-info | jq '.stream_info.length'

echo "=========================================="
echo "🎯 删除操作测试完成"
