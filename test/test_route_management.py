#!/usr/bin/env python3
"""
测试路由管理和同步功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_trigger_sync():
    """测试手动触发配置同步"""
    print("🧪 测试手动配置同步...")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/sync/trigger")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 同步触发成功:")
            print(f"   消息: {data.get('message')}")
            print(f"   实例ID: {data.get('instance_id')}")
            print(f"   耗时(ms): {data.get('duration_ms')}")
            print(f"   同步时间: {data.get('sync_time')}")
        else:
            print(f"❌ 同步失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_route_details():
    """测试获取路由详情"""
    print("\n🧪 测试路由详情...")
    
    # 先创建一个测试路由
    test_route = {
        "id": "detail-test-route",
        "path": "/api/detail-test",
        "method": "GET",
        "handler": "sandbox",
        "sandbox_type": "python",
        "code": "print('Detail test route')",
        "timeout": 5
    }
    
    try:
        # 创建路由
        create_response = requests.post(
            f"{BASE_URL}/admin/routes",
            json=test_route
        )
        
        if create_response.status_code in [200, 201]:
            print("✅ 测试路由创建成功")
            
            # 获取路由详情
            detail_response = requests.get(
                f"{BASE_URL}/admin/routes/detail-test-route/details"
            )
            
            if detail_response.status_code == 200:
                data = detail_response.json()
                print("✅ 路由详情:")
                print(f"   内存中存在: {data.get('in_memory')}")
                print(f"   版本: {data.get('version')}")
                
                route_data = data.get('route', {})
                print(f"   路由ID: {route_data.get('id')}")
                print(f"   路径: {route_data.get('path')}")
                
                redis_data = data.get('redis_data', {})
                if redis_data:
                    print(f"   Redis数据: {redis_data.get('id')}")
            else:
                print(f"❌ 获取详情失败: {detail_response.text}")
                
            # 清理测试路由
            requests.delete(f"{BASE_URL}/admin/routes/detail-test-route")
            
        else:
            print(f"❌ 创建测试路由失败: {create_response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_cleanup_events():
    """测试清理事件流"""
    print("\n🧪 测试事件清理...")
    
    cleanup_data = {
        "max_age_hours": 1  # 清理1小时前的事件
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/events/cleanup",
            json=cleanup_data
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 事件清理成功:")
            print(f"   消息: {data.get('message')}")
            print(f"   删除数量: {data.get('deleted_count')}")
            print(f"   最大年龄(小时): {data.get('max_age_hours')}")
            print(f"   截止时间: {data.get('cutoff_time')}")
        else:
            print(f"❌ 清理失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_incremental_sync_scenario():
    """测试增量同步场景"""
    print("\n🧪 测试增量同步场景...")
    
    try:
        # 获取初始状态
        initial_response = requests.get(f"{BASE_URL}/admin/config/version")
        if initial_response.status_code == 200:
            initial_data = initial_response.json()
            initial_version = initial_data.get('global_version')
            initial_route_count = initial_data.get('total_routes', 0)
            
            print(f"初始版本: {initial_version}")
            print(f"初始路由数: {initial_route_count}")
            
            # 创建多个测试路由
            for i in range(3):
                route = {
                    "id": f"sync-test-{i}",
                    "path": f"/api/sync-test-{i}",
                    "method": "GET",
                    "handler": "sandbox",
                    "sandbox_type": "python",
                    "code": f"print('Sync test {i}')",
                    "timeout": 5
                }
                
                requests.post(f"{BASE_URL}/admin/routes", json=route)
            
            print("✅ 创建了3个测试路由")
            
            # 触发同步
            sync_response = requests.post(f"{BASE_URL}/admin/sync/trigger")
            if sync_response.status_code == 200:
                print("✅ 手动同步完成")
                
                # 检查同步后状态
                final_response = requests.get(f"{BASE_URL}/admin/config/version")
                if final_response.status_code == 200:
                    final_data = final_response.json()
                    final_version = final_data.get('global_version')
                    final_route_count = final_data.get('total_routes', 0)
                    
                    print(f"最终版本: {final_version}")
                    print(f"最终路由数: {final_route_count}")
                    print(f"版本变化: {initial_version != final_version}")
                    print(f"路由数变化: {final_route_count - initial_route_count}")
            
            # 清理测试路由
            for i in range(3):
                requests.delete(f"{BASE_URL}/admin/routes/sync-test-{i}")
                
        else:
            print("❌ 无法获取初始状态")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始路由管理和同步测试")
    print("=" * 50)
    
    test_trigger_sync()
    test_route_details()
    test_cleanup_events()
    test_incremental_sync_scenario()
    
    print("\n" + "=" * 50)
    print("🎯 路由管理测试完成")
