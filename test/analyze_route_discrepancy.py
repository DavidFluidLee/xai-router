#!/usr/bin/env python3
"""
分析内存路由和Redis路由数量不一致的原因
"""

import requests
import json

ADMIN_URL = "http://localhost:8081"

def analyze_routes():
    print("🔍 分析内存路由 vs Redis路由数量差异")
    print("=" * 50)
    
    # 获取当前状态
    config_response = requests.get(f"{ADMIN_URL}/admin/config/version", timeout=10)
    config_data = config_response.json()
    
    memory_routes = config_data.get('memory_routes', 0)
    redis_routes = config_data.get('total_routes', 0)
    
    print(f"📊 当前状态:")
    print(f"   内存路由数: {memory_routes}")
    print(f"   Redis路由数: {redis_routes}")
    print(f"   差异: {memory_routes - redis_routes}")
    
    # 获取内存中的路由列表
    routes_response = requests.get(f"{ADMIN_URL}/admin/routes", timeout=10)
    if routes_response.status_code == 200:
        routes_data = routes_response.json()
        memory_route_list = routes_data.get('routes', [])
        
        print(f"\n🛣️ 内存中的路由 ({len(memory_route_list)}):")
        for route in memory_route_list:
            route_id = route.get('id', 'Unknown')
            path = route.get('path', 'Unknown')
            print(f"   - {route_id}: {path}")
    
    # 检查是否有测试路由
    print(f"\n🔎 检查可能的测试路由:")
    test_route_ids = [
        "detail-test-route", "sync-test-0", "sync-test-1", "sync-test-2",
        "integration-test-route", "basic-test-route", "final-comprehensive-test"
    ]
    
    for test_id in test_route_ids:
        detail_response = requests.get(f"{ADMIN_URL}/admin/routes/{test_id}/details", timeout=5)
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            in_memory = detail_data.get('in_memory', False)
            redis_data = detail_data.get('redis_data', {})
            has_redis = bool(redis_data and redis_data.get('id'))
            
            status = "内存+Redis" if in_memory and has_redis else "仅内存" if in_memory else "不存在"
            print(f"   - {test_id}: {status}")
    
    # 分析可能的原因
    print(f"\n💡 差异原因分析:")
    if memory_routes > redis_routes:
        print(f"   ✅ 正常现象: 有 {memory_routes - redis_routes} 个路由只在内存中")
        print(f"      可能原因:")
        print(f"      1. 测试路由创建后未持久化到Redis")
        print(f"      2. 路由正在创建过程中")
        print(f"      3. 增量同步尚未完成")
    elif memory_routes < redis_routes:
        print(f"   ⚠️ 异常现象: Redis中的路由比内存多")
        print(f"      可能原因:")
        print(f"      1. 内存中的路由被删除但Redis未同步")
        print(f"      2. 配置同步出现问题")
    else:
        print(f"   ✅ 完美同步: 内存和Redis路由数量一致")

def check_redis_directly():
    """直接检查Redis中的路由"""
    print(f"\n🔧 直接检查Redis状态:")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # 检查路由哈希表
        route_count = r.hlen("gateway:routes")
        print(f"   Redis gateway:routes 哈希表路由数: {route_count}")
        
        # 检查所有相关键
        print(f"   Redis中所有gateway相关键:")
        gateway_keys = r.keys("gateway:*")
        for key in gateway_keys:
            key_type = r.type(key)
            if key_type == "hash":
                count = r.hlen(key)
                print(f"     - {key} ({key_type}): {count} 项")
            elif key_type == "set":
                members = r.smembers(key)
                print(f"     - {key} ({key_type}): {len(members)} 成员")
            else:
                print(f"     - {key} ({key_type})")
                
    except ImportError:
        print("   ℹ️ 需要redis-py库来直接检查Redis")
    except Exception as e:
        print(f"   ❌ Redis检查失败: {e}")

def cleanup_test_routes():
    """清理可能的测试路由"""
    print(f"\n🧹 清理测试路由:")
    
    test_route_ids = [
        "detail-test-route", "sync-test-0", "sync-test-1", "sync-test-2",
        "integration-test-route", "basic-test-route", "final-comprehensive-test"
    ]
    
    cleaned_count = 0
    for test_id in test_route_ids:
        # 检查路由是否存在
        detail_response = requests.get(f"{ADMIN_URL}/admin/routes/{test_id}/details", timeout=5)
        if detail_response.status_code == 200:
            # 删除路由
            delete_response = requests.delete(f"{ADMIN_URL}/admin/routes/{test_id}", timeout=5)
            if delete_response.status_code == 200:
                print(f"   ✅ 已删除: {test_id}")
                cleaned_count += 1
            else:
                print(f"   ❌ 删除失败: {test_id}")
    
    if cleaned_count > 0:
        print(f"   总共清理了 {cleaned_count} 个测试路由")
        
        # 重新检查状态
        config_response = requests.get(f"{ADMIN_URL}/admin/config/version", timeout=10)
        config_data = config_response.json()
        memory_routes = config_data.get('memory_routes', 0)
        redis_routes = config_data.get('total_routes', 0)
        
        print(f"\n📊 清理后状态:")
        print(f"   内存路由数: {memory_routes}")
        print(f"   Redis路由数: {redis_routes}")
    else:
        print(f"   ℹ️ 没有找到需要清理的测试路由")

if __name__ == "__main__":
    analyze_routes()
    check_redis_directly()
    
    # 询问是否清理测试路由
    print(f"\n🧹 是否清理测试路由? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        cleanup_test_routes()
    else:
        print("   跳过清理")
    
    print(f"\n🎯 分析完成!")
