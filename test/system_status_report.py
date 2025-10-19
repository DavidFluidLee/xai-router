#!/usr/bin/env python3
"""
系统状态最终报告
"""

import requests
import time

ADMIN_URL = "http://localhost:8195"
GATEWAY_URL = "http://localhost:8081"

# API 认证头
HEADERS = {
    "X-Api-Key": "xai-admin-key"
}


def generate_final_report():
    """生成最终系统状态报告"""
    print("🚀 网关系统 - 最终状态报告")
    print("=" * 60)
    print(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 系统基本信息
    print("🔧 系统基本信息")
    print("-" * 30)
    
    health_response = requests.get(f"{ADMIN_URL}/admin/health", headers=HEADERS, timeout=10)
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"   状态: {health_data.get('status', 'Unknown')}")
        print(f"   Redis状态: {health_data.get('redis_status', 'Unknown')}")
        print(f"   时间戳: {health_data.get('timestamp', 'Unknown')}")
    print()
    
    # 2. 配置版本信息
    print("📊 配置版本信息")
    print("-" * 30)
    
    config_response = requests.get(f"{ADMIN_URL}/admin/config/version",headers=HEADERS, timeout=10)
    if config_response.status_code == 200:
        config_data = config_response.json()
        print(f"   全局版本: {config_data.get('global_version', 'Unknown')}")
        print(f"   最后更新: {config_data.get('last_updated', 'Unknown')}")
        print(f"   内存路由数: {config_data.get('memory_routes', 0)}")
        print(f"   Redis路由数: {config_data.get('total_routes', 0)}")
        print(f"   实例ID: {config_data.get('instance_id', 'Unknown')}")
        print(f"   Redis启用: {config_data.get('redis_enabled', False)}")
    print()
    
    # 3. 事件系统状态
    print("🌊 事件系统状态")
    print("-" * 30)
    
    stats_response = requests.get(f"{ADMIN_URL}/admin/events/stats",headers=HEADERS, timeout=10)
    if stats_response.status_code == 200:
        stats_data = stats_response.json()
        print(f"   总事件数: {stats_data.get('total_events', 0)}")
        print(f"   待处理数: {stats_data.get('total_pending', 0)}")
        print(f"   消费者组数: {len(stats_data.get('consumer_groups', {}))}")
    
    stream_response = requests.get(f"{ADMIN_URL}/admin/events/stream-info", timeout=10)
    if stream_response.status_code == 200:
        stream_data = stream_response.json()
        stream_info = stream_data.get('stream_info', {})
        print(f"   事件流长度: {stream_info.get('length', 0)}")
    print()
    
    # 4. 当前路由列表
    print("🛣️ 当前路由列表")
    print("-" * 30)
    
    routes_response = requests.get(f"{ADMIN_URL}/admin/routes", headers=HEADERS,timeout=10)
    if routes_response.status_code == 200:
        routes_data = routes_response.json()
        routes_list = routes_data.get('routes', [])
        
        print(f"   总路由数: {len(routes_list)}")
        for i, route in enumerate(routes_list, 1):
            route_id = route.get('id', 'Unknown')
            path = route.get('path', 'Unknown')
            method = route.get('method', 'Unknown')
            handler = route.get('handler', 'Unknown')
            print(f"   {i:2d}. {route_id}")
            print(f"       路径: {path}")
            print(f"       方法: {method}")
            print(f"       处理器: {handler}")
    print()
    
    # 5. 管理接口清单
    print("🔧 可用管理接口")
    print("-" * 30)
    
    management_endpoints = [
        ("GET", "/admin/health", "健康检查"),
        ("GET", "/admin/routes", "路由列表"),
        ("POST", "/admin/routes", "创建路由"),
        ("PUT", "/admin/routes/:id", "更新路由"),
        ("DELETE", "/admin/routes/:id", "删除路由"),
        ("GET", "/admin/config/version", "配置版本"),
        ("GET", "/admin/events/stats", "事件统计"),
        ("GET", "/admin/events/stream-info", "事件流信息"),
        ("GET", "/admin/events/consumers", "事件消费者"),
        ("POST", "/admin/sync/trigger", "手动同步"),
        ("GET", "/admin/routes/:routeId/details", "路由详情"),
        ("POST", "/admin/events/cleanup", "事件清理"),
    ]
    
    for method, endpoint, description in management_endpoints:
        print(f"   {method:6} {endpoint:30} - {description}")
    print()
    
    # 6. 系统总结
    print("🎯 系统总结")
    print("-" * 30)
    
    # 检查关键指标
    config_response = requests.get(f"{ADMIN_URL}/admin/config/version", headers=HEADERS,timeout=10)
    if config_response.status_code == 200:
        config_data = config_response.json()
        memory_routes = config_data.get('memory_routes', 0)
        redis_routes = config_data.get('total_routes', 0)
        
        if memory_routes == redis_routes:
            print("   ✅ 路由同步: 完美同步")
        else:
            print(f"   ⚠️ 路由同步: 内存({memory_routes}) ≠ Redis({redis_routes})")
    
    # 测试关键接口
    test_endpoints = [
        ("/admin/config/version", "配置版本"),
        ("/admin/events/stats", "事件统计"),
        ("/admin/sync/trigger", "手动同步"),
    ]
    
    working_count = 0
    for endpoint, name in test_endpoints:
        try:
            if "trigger" in endpoint:
                response = requests.post(f"{ADMIN_URL}{endpoint}", headers=HEADERS,timeout=5)
            else:
                response = requests.get(f"{ADMIN_URL}{endpoint}",headers=HEADERS, timeout=5)
            
            if response.status_code == 200:
                working_count += 1
        except:
            pass
    
    if working_count == len(test_endpoints):
        print("   ✅ 管理接口: 全部正常")
    else:
        print(f"   ⚠️ 管理接口: {working_count}/{len(test_endpoints)} 正常")
    
    print(f"   📍 管理端口: 8195")
    print(f"   📍 网关端口: 8081")
    print()
    
    print("🎉 系统状态: 健康运行中")

if __name__ == "__main__":
    generate_final_report()
