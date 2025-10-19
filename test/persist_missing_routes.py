#!/usr/bin/env python3
"""
将缺失的路由持久化到 Redis
"""

import requests
import json

ADMIN_URL = "http://localhost:8081"

def persist_missing_routes():
    """将 init-event-1 和 init-event-2 持久化到 Redis"""
    print("🔧 将缺失的路由持久化到 Redis")
    print("=" * 50)
    
    missing_routes = ["init-event-1", "init-event-2"]
    
    for route_id in missing_routes:
        print(f"\n🛣️ 处理路由: {route_id}")
        
        # 首先检查路由详情
        detail_response = requests.get(f"{ADMIN_URL}/admin/routes/{route_id}/details", timeout=10)
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            route_data = detail_data.get('route', {})
            
            print(f"   内存中的路由数据:")
            print(f"     - 路径: {route_data.get('path')}")
            print(f"     - 处理器: {route_data.get('handler')}")
            print(f"     - 沙箱类型: {route_data.get('sandbox_type')}")
            
            # 使用更新操作来触发持久化
            update_response = requests.put(f"{ADMIN_URL}/admin/routes/{route_id}", 
                                         json=route_data, timeout=10)
            
            if update_response.status_code == 200:
                print(f"   ✅ 路由 {route_id} 已持久化到 Redis")
            else:
                print(f"   ❌ 持久化失败: {update_response.text}")
        else:
            print(f"   ❌ 无法获取路由详情: {detail_response.text}")
    
    # 验证结果
    print(f"\n📊 验证持久化结果:")
    config_response = requests.get(f"{ADMIN_URL}/admin/config/version", timeout=10)
    config_data = config_response.json()
    
    memory_routes = config_data.get('memory_routes', 0)
    redis_routes = config_data.get('total_routes', 0)
    
    print(f"   内存路由数: {memory_routes}")
    print(f"   Redis路由数: {redis_routes}")
    print(f"   差异: {memory_routes - redis_routes}")

def trigger_sync():
    """触发配置同步"""
    print(f"\n🔄 触发配置同步...")
    response = requests.post(f"{ADMIN_URL}/admin/sync/trigger", timeout=10)
    if response.status_code == 200:
        print("   ✅ 同步触发成功")
    else:
        print(f"   ❌ 同步失败: {response.text}")

if __name__ == "__main__":
    persist_missing_routes()
    trigger_sync()
