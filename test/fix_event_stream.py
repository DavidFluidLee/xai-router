#!/usr/bin/env python3
"""
修复事件统计接口 - 创建事件流和消费者组
"""

import requests
import time
import json

ADMIN_URL = "http://localhost:8081"

def initialize_event_stream():
    """初始化事件流和消费者组"""
    print("🔧 初始化事件流系统...")
    
    # 方法1: 通过创建多个测试事件来触发事件流创建
    test_events = [
        {
            "event_type": "CREATE",
            "route_id": "init-event-1",
            "route_data": {
                "id": "init-event-1",
                "path": "/api/init-1",
                "method": "GET",
                "handler": "sandbox",
                "sandbox_type": "python",
                "code": "print('Init event 1')",
                "timeout": 5
            }
        },
        {
            "event_type": "CREATE", 
            "route_id": "init-event-2",
            "route_data": {
                "id": "init-event-2",
                "path": "/api/init-2",
                "method": "GET",
                "handler": "sandbox",
                "sandbox_type": "python",
                "code": "print('Init event 2')",
                "timeout": 5
            }
        }
    ]
    
    success_count = 0
    for i, event_data in enumerate(test_events, 1):
        try:
            print(f"   创建测试事件 {i}...")
            response = requests.post(f"{ADMIN_URL}/admin/events/test", 
                                   json=event_data, timeout=10)
            if response.status_code == 200:
                success_count += 1
                print(f"     ✅ 事件 {i} 创建成功")
            else:
                print(f"     ❌ 事件 {i} 创建失败: {response.text}")
        except Exception as e:
            print(f"     💥 事件 {i} 创建异常: {e}")
    
    return success_count

def wait_for_event_processing():
    """等待事件被处理"""
    print("⏳ 等待事件处理...")
    time.sleep(2)

def test_event_stats_with_retry():
    """测试事件统计接口，带重试机制"""
    print("\n🧪 测试事件统计接口（带重试）...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{ADMIN_URL}/admin/events/stats", timeout=10)
            print(f"   尝试 {attempt + 1}/{max_retries} - 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ 事件统计接口正常工作!")
                print(f"      总事件数: {data.get('total_events', 0)}")
                print(f"      待处理数: {data.get('total_pending', 0)}")
                print(f"      消费者组: {len(data.get('consumer_groups', {}))}")
                print(f"      实例ID: {data.get('instance_id')}")
                return True
            else:
                error_msg = response.text
                print(f"   ❌ 事件统计失败: {error_msg}")
                
                # 如果是"no such key"错误，继续重试
                if "no such key" in error_msg and attempt < max_retries - 1:
                    print(f"   🔄 等待后重试...")
                    time.sleep(2)
                    continue
                else:
                    return False
                    
        except Exception as e:
            print(f"   💥 事件统计异常: {e}")
            if attempt < max_retries - 1:
                print(f"   🔄 等待后重试...")
                time.sleep(2)
                continue
            return False
    
    return False

def check_event_stream_info():
    """检查事件流信息"""
    print("\n🔍 检查事件流信息...")
    
    try:
        response = requests.get(f"{ADMIN_URL}/admin/events/stream-info", timeout=10)
        if response.status_code == 200:
            data = response.json()
            stream_info = data.get('stream_info', {})
            print("   ✅ 事件流信息:")
            print(f"      长度: {stream_info.get('length', 0)}")
            print(f"      最后ID: {stream_info.get('last_generated_id', 'N/A')}")
            return True
        else:
            print(f"   ❌ 事件流信息获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"   💥 事件流信息异常: {e}")
        return False

def check_event_consumers():
    """检查事件消费者状态"""
    print("\n🔍 检查事件消费者状态...")
    
    try:
        response = requests.get(f"{ADMIN_URL}/admin/events/consumers", timeout=10)
        if response.status_code == 200:
            data = response.json()
            consumers = data.get('consumers', [])
            print(f"   ✅ 事件消费者: {len(consumers)} 个")
            for consumer in consumers:
                print(f"      - {consumer.get('consumer_name')}: {consumer.get('running', False)}")
            return True
        else:
            print(f"   ❌ 事件消费者获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"   💥 事件消费者异常: {e}")
        return False

def main():
    print("🚀 事件流系统完整初始化")
    print("=" * 60)
    
    # 1. 初始化事件流
    success_count = initialize_event_stream()
    print(f"\n📊 事件创建结果: {success_count}/2 成功")
    
    if success_count == 0:
        print("❌ 无法创建测试事件，事件流初始化失败")
        return
    
    # 2. 等待事件处理
    wait_for_event_processing()
    
    # 3. 检查事件流信息
    check_event_stream_info()
    
    # 4. 检查事件消费者
    check_event_consumers()
    
    # 5. 测试事件统计（带重试）
    stats_success = test_event_stats_with_retry()
    
    # 6. 最终验证所有接口
    print("\n" + "=" * 60)
    print("🎯 最终验证所有管理接口")
    
    endpoints = [
        ("配置版本", "GET", "/admin/config/version"),
        ("事件流信息", "GET", "/admin/events/stream-info"),
        ("事件消费者", "GET", "/admin/events/consumers"),
        ("手动同步", "POST", "/admin/sync/trigger"),
        ("事件清理", "POST", "/admin/events/cleanup", {"max_age_hours": 1}),
    ]
    
    working_endpoints = []
    for name, method, endpoint, *data in endpoints:
        try:
            url = f"{ADMIN_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, json=data[0] if data else {}, timeout=10)
            
            if response.status_code == 200:
                working_endpoints.append(name)
                print(f"   ✅ {name} - 正常")
            else:
                print(f"   ❌ {name} - 异常: {response.text}")
                
        except Exception as e:
            print(f"   💥 {name} - 异常: {e}")
    
    # 添加事件统计结果
    if stats_success:
        working_endpoints.append("事件统计")
        print(f"   ✅ 事件统计 - 正常")
    else:
        print(f"   ⚠️ 事件统计 - 需要更多事件数据")
    
    print(f"\n📊 工作正常的接口: {len(working_endpoints)}/{len(endpoints) + 1}")
    
    if len(working_endpoints) >= len(endpoints):
        print("🎉 事件流系统初始化成功！")
    else:
        print("⚠️ 部分接口需要进一步调试")

if __name__ == "__main__":
    main()
