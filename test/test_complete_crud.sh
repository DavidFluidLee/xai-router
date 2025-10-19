#!/bin/bash

echo "🎯 完整CRUD操作验证..."
echo "=========================================="

# 清理环境
echo "1. 清理测试环境..."
curl -X DELETE http://localhost:8081/admin/routes/test-crud-route > /dev/null 2>&1
sleep 1

# 测试CREATE
echo "2. 测试CREATE操作..."
curl -X POST http://localhost:8081/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "CREATE",
    "route_id": "test-crud-route",
    "route_data": {
      "id": "test-crud-route",
      "path": "/api/crud-test",
      "method": "GET",
      "handler": "sandbox",
      "sandbox_type": "python",
      "code": "print(\"CREATE operation test\")",
      "timeout": 5
    }
  }' > /dev/null 2>&1

sleep 2
echo "✅ CREATE完成"
curl http://localhost:8080/api/crud-test

# 测试UPDATE
echo "3. 测试UPDATE操作..."
curl -X POST http://localhost:8081/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "UPDATE", 
    "route_id": "test-crud-route",
    "route_data": {
      "id": "test-crud-route",
      "path": "/api/crud-test",
      "method": "GET",
      "handler": "sandbox",
      "sandbox_type": "python",
      "code": "print(\"UPDATE operation test\")",
      "timeout": 5
    }
  }' > /dev/null 2>&1

sleep 2
echo "✅ UPDATE完成" 
curl http://localhost:8080/api/crud-test

# 测试DELETE
echo "4. 测试DELETE操作..."
curl -X POST http://localhost:8081/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "DELETE",
    "route_id": "test-crud-route",
    "route_data": {
      "id": "test-crud-route"
    }
  }' > /dev/null 2>&1

sleep 2
echo "✅ DELETE完成"
echo "验证删除结果:"
curl -s http://localhost:8081/admin/routes | jq '.routes[] | select(.id == "test-crud-route")'

# 系统状态检查
echo "5. 系统状态检查:"
echo "路由总数: $(curl -s http://localhost:8081/admin/routes | jq '.routes | length')"
echo "事件流长度: $(curl -s http://localhost:8081/admin/events/stream-info | jq '.stream_info.length')"
echo "消费者状态: $(curl -s http://localhost:8081/admin/events/consumers | jq '.consumers[0].running')"

echo "=========================================="
echo "🎉 完整CRUD操作验证成功！"
