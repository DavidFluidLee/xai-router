#!/bin/bash

echo "🚀 开始集成测试 - 新增管理接口和路由管理功能"
echo "=========================================="

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 2

# 测试健康检查
echo ""
echo "1. 测试健康检查端点"
curl -s http://localhost:8080/admin/health | jq '.'
sleep 1

# 测试配置版本
echo ""
echo "2. 测试配置版本信息"
curl -s http://localhost:8080/admin/config/version | jq '.'
sleep 1

# 测试事件统计
echo ""
echo "3. 测试事件统计"
curl -s http://localhost:8080/admin/events/stats | jq '.'
sleep 1

# 测试创建路由并检查详情
echo ""
echo "4. 测试路由创建和详情"
ROUTE_ID="integration-test-$(date +%s)"

# 创建路由
curl -X POST http://localhost:8080/admin/routes \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$ROUTE_ID\",
    \"path\": \"/api/integration-test\",
    \"method\": \"GET\",
    \"handler\": \"sandbox\", 
    \"sandbox_type\": \"python\",
    \"code\": \"print('Integration test successful')\",
    \"timeout\": 5
  }"

sleep 1

# 获取路由详情
echo ""
echo "路由详情:"
curl -s http://localhost:8080/admin/routes/$ROUTE_ID/details | jq '.'
sleep 1

# 测试手动同步
echo ""
echo "5. 测试手动配置同步"
curl -X POST http://localhost:8080/admin/sync/trigger | jq '.'
sleep 1

# 测试事件清理（不实际执行，只检查接口）
echo ""
echo "6. 测试事件清理接口"
curl -X POST http://localhost:8080/admin/events/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 1}' | jq '.'
sleep 1

# 清理测试路由
echo ""
echo "7. 清理测试路由"
curl -X DELETE http://localhost:8080/admin/routes/$ROUTE_ID

echo ""
echo "=========================================="
echo "🎯 集成测试完成"
