#!/usr/bin/env python3
"""
修复事件统计接口 - 初始化事件流
"""

import requests
import time

ADMIN_URL = "http://localhost:8081"

def create_test_event():
    """创建测试事件来初始化事件流"""
    print("🎯 创建测试事件初始化事件流...")
    
    test_event = {
        "event_type": "CREATE",
        "route_id": "test-event-route",
        "route_data": {
            "id": "test-event-route",
            "path": "/api/test-event",
            "method": "GET",
            "handler": "sandbox",
            "sandbox_type": "python",
            "code": "print('Test event')",
            "timeout": 5
        }
    }
    
    try:
        response = requests.post(f"{ADMIN_URL}/admin/events/test", json=test_event, timeout=10)
        if response.status_code == 200:
            print("✅ 测试事件创建成功")
            return True
        else:
            print(f"❌ 测试事件创建失败: {response.text}")
            return False
    except Exception as e:
        print(f"💥 创建测试事件异常: {e}")
        return False

def test_event_stats():
    """测试事件统计接口"""
    print("\n🧪 测试事件统计接口...")
    
    try:
        response = requests.get(f"{ADMIN_URL}/admin/events/stats", timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 事件统计:")
            print(f"   总事件数: {data.get('total_events')}")
            print(f"   待处理数: {data.get('total_pending')}")
            print(f"   消费者组数: {len(data.get('consumer_groups', {}))}")
            print(f"   实例ID: {data.get('instance_id')}")
            return True
        else:
            print(f"❌ 事件统计失败: {response.text}")
            return False
    except Exception as e:
        print(f"💥 事件统计异常: {e}")
        return False

def test_all_new_endpoints():
    """完整测试所有新接口"""
    print("🚀 完整测试所有新增管理接口")
    print("=" * 60)
    
    # 先创建测试事件来初始化事件流
    if create_test_event():
        # 等待事件处理
        time.sleep(1)
        
        # 现在测试事件统计
        test_event_stats()
    
    # 测试其他接口
    print("\n" + "=" * 60)
    print("🧪 测试其他新增接口")
    
    endpoints = [
        ("配置版本", "GET", "/admin/config/version"),
        ("手动同步", "POST", "/admin/sync/trigger"),
        ("事件清理", "POST", "/admin/events/cleanup", {"max_age_hours": 1}),
    ]
    
    for name, method, endpoint, *data in endpoints:
        print(f"\n🔍 {name}: {method} {endpoint}")
        try:
            url = f"{ADMIN_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data[0] if data else {}, timeout=10)
            
            print(f"   状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 成功")
                if "message" in result:
                    print(f"   消息: {result['message']}")
            else:
                print(f"   ❌ 失败: {response.text}")
                
        except Exception as e:
            print(f"   💥 异常: {e}")

if __name__ == "__main__":
    test_all_new_endpoints()
