#!/usr/bin/env python3
"""
清理测试路由 init-event-1 和 init-event-2
"""

import requests

ADMIN_URL = "http://localhost:8081"

def cleanup_test_routes():
    """清理 init-event-1 和 init-event-2 路由"""
    print("🧹 清理测试路由")
    print("=" * 50)
    
    test_routes = ["init-event-1", "init-event-2"]
    
    for route_id in test_routes:
        print(f"\n🗑️ 删除路由: {route_id}")
        
        # 检查路由是否存在
        detail_response = requests.get(f"{ADMIN_URL}/admin/routes/{route_id}/details", timeout=10)
        if detail_response.status_code == 200:
            # 删除路由
            delete_response = requests.delete(f"{ADMIN_URL}/admin/routes/{route_id}", timeout=10)
            if delete_response.status_code == 200:
                print(f"   ✅ 路由 {route_id} 已删除")
            else:
                print(f"   ❌ 删除失败: {delete_response.text}")
        else:
            print(f"   ℹ️ 路由 {route_id} 不存在或无法访问")
    
    # 验证结果
    print(f"\n📊 验证清理结果:")
    config_response = requests.get(f"{ADMIN_URL}/admin/config/version", timeout=10)
    config_data = config_response.json()
    
    memory_routes = config_data.get('memory_routes', 0)
    redis_routes = config_data.get('total_routes', 0)
    
    print(f"   内存路由数: {memory_routes}")
    print(f"   Redis路由数: {redis_routes}")
    print(f"   差异: {memory_routes - redis_routes}")

if __name__ == "__main__":
    cleanup_test_routes()
