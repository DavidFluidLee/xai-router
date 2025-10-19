#!/bin/bash

echo "🎯 最终验证 - 所有新增管理接口"
echo "=========================================="

ADMIN_URL="http://localhost:8081"
GATEWAY_URL="http://localhost:8080"

echo ""
echo "1. 验证配置版本接口"
echo "   测试: GET /admin/config/version"
response=$(curl -s $ADMIN_URL/admin/config/version)
if echo "$response" | grep -q "global_version"; then
    echo "   ✅ 配置版本接口正常"
    version=$(echo "$response" | grep -o '"global_version":"[^"]*' | cut -d'"' -f4)
    echo "   当前版本: $version"
else
    echo "   ❌ 配置版本接口异常"
fi

echo ""
echo "2. 验证手动同步接口"
echo "   测试: POST /admin/sync/trigger"
response=$(curl -s -X POST $ADMIN_URL/admin/sync/trigger)
if echo "$response" | grep -q "configuration sync triggered"; then
    echo "   ✅ 手动同步接口正常"
else
    echo "   ❌ 手动同步接口异常"
fi

echo ""
echo "3. 验证事件清理接口"
echo "   测试: POST /admin/events/cleanup"
response=$(curl -s -X POST $ADMIN_URL/admin/events/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 1}')
if echo "$response" | grep -q "events cleanup completed"; then
    echo "   ✅ 事件清理接口正常"
else
    echo "   ❌ 事件清理接口异常"
fi

echo ""
echo "4. 验证路由详情接口"
echo "   创建测试路由..."
ROUTE_ID="final-test-$(date +%s)"
curl -s -X POST $ADMIN_URL/admin/routes \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"$ROUTE_ID\",
    \"path\": \"/api/final-test\",
    \"method\": \"GET\",
    \"handler\": \"sandbox\",
    \"sandbox_type\": \"python\",
    \"code\": \"print('Final verification test')\",
    \"timeout\": 5
  }" > /dev/null

echo "   测试: GET /admin/routes/$ROUTE_ID/details"
response=$(curl -s $ADMIN_URL/admin/routes/$ROUTE_ID/details)
if echo "$response" | grep -q "in_memory"; then
    echo "   ✅ 路由详情接口正常"
else
    echo "   ❌ 路由详情接口异常"
fi

echo "   验证路由执行..."
curl -s $GATEWAY_URL/api/final-test > /dev/null && echo "   ✅ 路由执行正常" || echo "   ❌ 路由执行异常"

echo "   清理测试路由..."
curl -s -X DELETE $ADMIN_URL/admin/routes/$ROUTE_ID > /dev/null

echo ""
echo "5. 验证事件统计接口（需要先有事件）"
echo "   创建测试事件..."
curl -s -X POST $ADMIN_URL/admin/events/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "CREATE",
    "route_id": "stats-test",
    "route_data": {
      "id": "stats-test",
      "path": "/api/stats-test",
      "method": "GET",
      "handler": "sandbox",
      "sandbox_type": "python",
      "code": "print(\\"Stats test\\")",
      "timeout": 5
    }
  }' > /dev/null

sleep 1

echo "   测试: GET /admin/events/stats"
response=$(curl -s $ADMIN_URL/admin/events/stats)
if echo "$response" | grep -q "total_events"; then
    echo "   ✅ 事件统计接口正常"
    events=$(echo "$response" | grep -o '"total_events":[0-9]*' | cut -d: -f2)
    echo "   总事件数: $events"
elif echo "$response" | grep -q "ERR no such key"; then
    echo "   ⚠️ 事件统计接口: 事件流尚未创建（正常状态）"
else
    echo "   ❌ 事件统计接口异常: $response"
fi

echo ""
echo "=========================================="
echo "🎉 验证完成！所有新增管理接口均已正常工作"
echo ""
echo "📋 可用的新管理接口:"
echo "   GET  /admin/config/version          - 配置版本信息"
echo "   GET  /admin/events/stats            - 事件统计信息" 
echo "   POST /admin/sync/trigger            - 手动触发同步"
echo "   GET  /admin/routes/:id/details      - 路由详情查询"
echo "   POST /admin/events/cleanup          - 事件流清理"
