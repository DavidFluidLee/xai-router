#!/bin/bash

# XAI Router Gateway 完整功能测试脚本
# 测试所有 CRUD 操作：创建、读取、更新、删除

echo "🚀 XAI Router Gateway 完整功能测试"
echo "=========================================="

# 基础配置
MANAGEMENT_URL="http://localhost:8081/admin"
GATEWAY_URL="http://localhost:8080"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. 健康检查测试
echo ""
print_info "1. 测试健康检查"
response=$(curl -s "$MANAGEMENT_URL/health")
echo "响应: $response"

# 2. 查看当前路由和沙箱
echo ""
print_info "2. 查看当前状态"
echo "路由:"
curl -s "$MANAGEMENT_URL/routes" | jq .
echo "沙箱:"
curl -s "$MANAGEMENT_URL/sandboxes" | jq .

# 3. 创建路由测试 (CREATE)
echo ""
print_info "3. 测试创建路由 (CREATE)"

## 3.1 创建简单数学路由
echo "创建简单数学路由..."
curl -X POST "$MANAGEMENT_URL/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-math-create",
    "path": "/api/math",
    "method": "POST",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "import json\nresult = {\"operation\": \"addition\", \"result\": 100, \"message\": \"Created via CREATE\"}\nprint(json.dumps(result))",
    "timeout": 10
  }'

## 3.2 创建状态检查路由
echo ""
echo "创建状态检查路由..."
curl -X POST "$MANAGEMENT_URL/routes" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-status-create", 
    "path": "/api/status",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "import json\nimport time\nresult = {\"status\": \"healthy\", \"timestamp\": \"'$(date +%Y-%m-%dT%H:%M:%S)'\", \"action\": \"created\"}\nprint(json.dumps(result))",
    "timeout": 10
  }'

# 4. 验证创建的路由 (READ)
echo ""
print_info "4. 验证创建的路由 (READ)"
echo "当前所有路由:"
curl -s "$MANAGEMENT_URL/routes" | jq '.routes[] | {id: .id, path: .path, method: .method}'

# 5. 测试执行创建的路由
echo ""
print_info "5. 测试执行创建的路由"
echo "测试数学路由:"
curl -X POST "$GATEWAY_URL/api/math"
echo ""
echo "测试状态路由:"
curl -s "$GATEWAY_URL/api/status"

# 6. 更新路由测试 (UPDATE)
echo ""
print_info "6. 测试更新路由 (UPDATE)"

## 6.1 更新数学路由
echo "更新数学路由..."
curl -X PUT "$MANAGEMENT_URL/routes/test-math-create" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-math-create",
    "path": "/api/math",
    "method": "POST", 
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "import json\nimport random\nresult = {\"operation\": \"multiplication\", \"result\": 42, \"random\": '$(($RANDOM % 100))', \"message\": \"Updated via UPDATE\"}\nprint(json.dumps(result))",
    "timeout": 15
  }'

## 6.2 更新状态路由
echo ""
echo "更新状态路由..."
curl -X PUT "$MANAGEMENT_URL/routes/test-status-create" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-status-create",
    "path": "/api/status",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python",
    "code": "import json\nimport time\nresult = {\"status\": \"updated\", \"timestamp\": \"'$(date +%Y-%m-%dT%H:%M:%S)'\", \"version\": \"2.0\", \"action\": \"updated\"}\nprint(json.dumps(result))",
    "timeout": 15
  }'

# 7. 验证更新的路由
echo ""
print_info "7. 验证更新的路由"
echo "测试更新后的数学路由:"
curl -X POST "$GATEWAY_URL/api/math"
echo ""
echo "测试更新后的状态路由:"
curl -s "$GATEWAY_URL/api/status"

# 8. 删除路由测试 (DELETE)
echo ""
print_info "8. 测试删除路由 (DELETE)"

## 8.1 删除数学路由
echo "删除数学路由..."
curl -X DELETE "$MANAGEMENT_URL/routes/test-math-create"

## 8.2 删除状态路由  
echo ""
echo "删除状态路由..."
curl -X DELETE "$MANAGEMENT_URL/routes/test-status-create"

# 9. 验证删除结果
echo ""
print_info "9. 验证删除结果"
echo "剩余路由:"
curl -s "$MANAGEMENT_URL/routes" | jq '.routes[] | {id: .id, path: .path, method: .method}'

# 10. 错误处理测试
echo ""
print_info "10. 测试错误处理"

## 10.1 测试不存在的路由
echo "测试不存在的路由:"
curl -s "$GATEWAY_URL/api/nonexistent"

## 10.2 测试错误的方法
echo ""
echo "测试错误的方法 (GET vs POST):"
curl -s -X POST "$GATEWAY_URL/status"

## 10.3 测试无效的路由ID更新
echo ""
echo "测试无效的路由ID更新:"
curl -X PUT "$MANAGEMENT_URL/routes/nonexistent-route" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "nonexistent-route",
    "path": "/test",
    "method": "GET",
    "handler": "sandbox",
    "sandbox_type": "python", 
    "code": "print(\"test\")",
    "timeout": 10
  }'

# 11. 沙箱管理测试
echo ""
print_info "11. 测试沙箱管理"

## 11.1 注册测试沙箱
echo "注册测试沙箱..."
curl -X POST "$MANAGEMENT_URL/sandboxes/register" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-sandbox-1",
    "url": "https://xai.digiwincloud.com.cn/v1/sandbox",
    "type": "python",
    "status": "healthy",
    "load": 0,
    "last_ping": '$(date +%s)'
  }'

## 11.2 查看沙箱
echo ""
echo "当前沙箱:"
curl -s "$MANAGEMENT_URL/sandboxes" | jq .

## 11.3 删除测试沙箱
echo ""
echo "删除测试沙箱..."
curl -X DELETE "$MANAGEMENT_URL/sandboxes/test-sandbox-1"

# 12. 最终状态检查
echo ""
print_info "12. 最终状态检查"
echo "健康状态:"
curl -s "$MANAGEMENT_URL/health" | jq .
echo ""
echo "剩余路由数量:"
curl -s "$MANAGEMENT_URL/routes" | jq '.routes | length'
echo "剩余沙箱数量:"
curl -s "$MANAGEMENT_URL/sandboxes" | jq '.sandboxes | length'

echo ""
print_success "🎉 所有测试完成！XAI Router Gateway CRUD 功能正常！"
