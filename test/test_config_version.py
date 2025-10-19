#!/usr/bin/env python3
"""
测试配置版本和状态相关接口
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"

def test_config_version():
    """测试获取配置版本信息"""
    print("🧪 测试配置版本信息...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/config/version")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 配置版本信息:")
            print(f"   全局版本: {data.get('global_version')}")
            print(f"   最后更新: {data.get('last_updated')}")
            print(f"   更新中路由: {data.get('updating_routes', [])}")
            print(f"   总路由数: {data.get('total_routes')}")
            print(f"   内存路由数: {data.get('memory_routes')}")
            print(f"   实例ID: {data.get('instance_id')}")
            print(f"   Redis启用: {data.get('redis_enabled')}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_health_check():
    """测试健康检查端点"""
    print("\n🧪 测试健康检查...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/health")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 健康状态:")
            print(f"   状态: {data.get('status')}")
            print(f"   时间戳: {data.get('timestamp')}")
            print(f"   实例ID: {data.get('instance_id')}")
            print(f"   Redis状态: {data.get('redis_status')}")
            print(f"   路由数量: {data.get('route_count')}")
            print(f"   配置版本: {data.get('config_version')}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_event_stats():
    """测试事件统计信息"""
    print("\n🧪 测试事件统计...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/events/stats")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 事件统计:")
            print(f"   总事件数: {data.get('total_events')}")
            print(f"   待处理数: {data.get('total_pending')}")
            print(f"   消费者组: {len(data.get('consumer_groups', {}))}")
            print(f"   内存路由数: {data.get('memory_route_count')}")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始配置版本和状态测试")
    print("=" * 50)
    
    test_config_version()
    test_health_check()
    test_event_stats()
    
    print("\n" + "=" * 50)
    print("🎯 配置版本测试完成")
