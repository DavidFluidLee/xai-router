#!/bin/bash

echo "🚀 测试新增的管理接口"
echo "=========================================="

ADMIN_URL="http://localhost:8081"

# 等待服务完全启动
echo "⏳ 等待服务启动..."
sleep 2

echo ""
echo "1. 测试配置版本信息"
curl -s $ADMIN_URL/admin/config/version | jq '.' 2>/dev/null || curl -s $ADMIN_URL/admin/config/version

echo ""
echo "2. 测试事件统计"
curl -s $ADMIN_URL/admin/events/stats | jq '.' 2>/dev/null || curl -s $ADMIN_URL/admin/events/stats

echo ""
echo "3. 测试手动同步"
curl -s -X POST $ADMIN_URL/admin/sync/trigger | jq '.' 2>/dev/null || curl -s -X POST $ADMIN_URL/admin/sync/trigger

echo ""
echo "4. 测试事件清理接口"
curl -s -X POST $ADMIN_URL/admin/events/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 1}' | jq '.' 2>/dev/null || curl -s -X POST $ADMIN_URL/admin/events/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 1}'

echo ""
echo "5. 创建测试路由并获取详情"
ROUTE_ID="test-route-$(date +%s)"

# 创建测试路由
echo "创建路由: $ROUTE_ID"
curl -s -X POST $ADMIN_URL/admin/routes \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$ROUTE_ID\",
    \"path\": \"/api/test-route\",
    \"method\": \"GET\",
    \"handler\": \"sandbox\",
    \"sandbox_type\": \"python\",
    \"code\": \"print('Test route successful')\",
    \"timeout\": 5
  }" | jq '.' 2>/dev/null || echo "创建路由响应"

sleep 1

echo ""
echo "获取路由详情:"
curl -s $ADMIN_URL/admin/routes/$ROUTE_ID/details | jq '.' 2>/dev/null || curl -s $ADMIN_URL/admin/routes/$ROUTE_ID/details

echo ""
echo "测试路由访问:"
curl -s http://localhost:8080/api/test-route || echo "路由访问响应"

echo ""
echo "清理测试路由:"
curl -s -X DELETE $ADMIN_URL/admin/routes/$ROUTE_ID | jq '.' 2>/dev/null || echo "删除路由响应"

echo ""
echo "=========================================="
echo "🎯 新增接口测试完成"
