#!/bin/bash

echo "🧪 测试CRUD立即生效..."
echo "=========================================="

# 1. 测试CREATE立即生效
echo "1. 测试CREATE立即生效..."
curl -X POST http://localhost:8081/admin/routes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "immediate-test",
    "path": "/api/immediate",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "print(\"Immediate CREATE test\")",
    "timeout": 5
  }' > /dev/null 2>&1

# 立即测试路由是否可用
echo "CREATE后立即测试:"
curl http://localhost:8080/api/immediate
echo ""

# 2. 测试UPDATE立即生效
echo "2. 测试UPDATE立即生效..."
curl -X PUT http://localhost:8081/admin/routes/immediate-test \
  -H "Content-Type: application/json" \
  -d '{
    "id": "immediate-test", 
    "path": "/api/immediate",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "print(\"Immediate UPDATE test\")",
    "timeout": 5
  }' > /dev/null 2>&1

# 立即测试更新是否生效
echo "UPDATE后立即测试:"
curl http://localhost:8080/api/immediate
echo ""

# 3. 测试DELETE立即生效
echo "3. 测试DELETE立即生效..."
curl -X DELETE http://localhost:8081/admin/routes/immediate-test > /dev/null 2>&1

# 立即测试删除是否生效
echo "DELETE后立即测试:"
curl http://localhost:8080/api/immediate
echo ""

echo "=========================================="
echo "🎯 CRUD立即生效测试完成"
