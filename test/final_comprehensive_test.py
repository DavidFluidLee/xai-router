#!/usr/bin/env python3
"""
最终完整测试 - 验证所有新增管理接口
"""

import requests
import json
import time

ADMIN_URL = "http://localhost:8081"
GATEWAY_URL = "http://localhost:8080"

def print_success(message):
    print(f"✅ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_config_version():
    """测试配置版本接口"""
    print("\n🔧 测试配置版本接口")
    response = requests.get(f"{ADMIN_URL}/admin/config/version", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print_success(f"配置版本: {data.get('global_version')}")
        print_success(f"内存路由: {data.get('memory_routes')}")
        print_success(f"Redis路由: {data.get('total_routes')}")
        print_success(f"实例ID: {data.get('instance_id')}")
        return True
    return False

def test_event_stats():
    """测试事件统计接口"""
    print("\n📊 测试事件统计接口")
    response = requests.get(f"{ADMIN_URL}/admin/events/stats", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print_success(f"总事件数: {data.get('total_events')}")
        print_success(f"待处理数: {data.get('total_pending')}")
        print_success(f"消费者组: {len(data.get('consumer_groups', {}))}")
        return True
    return False

def test_event_stream_info():
    """测试事件流信息"""
    print("\n🌊 测试事件流信息")
    response = requests.get(f"{ADMIN_URL}/admin/events/stream-info", timeout=10)
    if response.status_code == 200:
        data = response.json()
        stream_info = data.get('stream_info', {})
        print_success(f"流长度: {stream_info.get('length', 0)}")
        print_success(f"最后ID: {stream_info.get('last_generated_id', 'N/A')}")
        return True
    return False

def test_event_consumers():
    """测试事件消费者"""
    print("\n👥 测试事件消费者")
    response = requests.get(f"{ADMIN_URL}/admin/events/consumers", timeout=10)
    if response.status_code == 200:
        data = response.json()
        consumers = data.get('consumers', [])
        print_success(f"消费者数量: {len(consumers)}")
        for consumer in consumers:
            status = "运行中" if consumer.get('running') else "已停止"
            print_success(f"  - {consumer.get('consumer_name')}: {status}")
        return True
    return False

def test_manual_sync():
    """测试手动同步"""
    print("\n🔄 测试手动同步")
    response = requests.post(f"{ADMIN_URL}/admin/sync/trigger", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print_success(f"同步完成: {data.get('message')}")
        print_success(f"耗时: {data.get('duration_ms')}ms")
        return True
    return False

def test_event_cleanup():
    """测试事件清理"""
    print("\n🧹 测试事件清理")
    response = requests.post(f"{ADMIN_URL}/admin/events/cleanup", 
                           json={"max_age_hours": 1}, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print_success(f"清理完成: {data.get('message')}")
        print_success(f"删除数量: {data.get('deleted_count')}")
        return True
    return False

def test_route_details():
    """测试路由详情"""
    print("\n🛣️ 测试路由详情")
    
    # 创建测试路由
    test_route = {
        "id": "final-comprehensive-test",
        "path": "/api/final-comprehensive",
        "method": "GET",
        "handler": "sandbox",
        "sandbox_type": "python",
        "code": "print('Final comprehensive test successful!')",
        "timeout": 5
    }
    
    # 创建路由
    create_resp = requests.post(f"{ADMIN_URL}/admin/routes", json=test_route, timeout=10)
    if create_resp.status_code not in [200, 201]:
        print("❌ 创建测试路由失败")
        return False
    
    print_success("测试路由创建成功")
    
    # 获取路由详情
    detail_resp = requests.get(f"{ADMIN_URL}/admin/routes/final-comprehensive-test/details", timeout=10)
    if detail_resp.status_code == 200:
        detail_data = detail_resp.json()
        print_success(f"内存中存在: {detail_data.get('in_memory')}")
        print_success(f"路由版本: {detail_data.get('version')}")
        
        # 测试路由执行
        route_resp = requests.get(f"{GATEWAY_URL}/api/final-comprehensive", timeout=10)
        if route_resp.status_code == 200:
            print_success("路由执行成功")
        else:
            print("❌ 路由执行失败")
    else:
        print("❌ 获取路由详情失败")
    
    # 清理测试路由
    delete_resp = requests.delete(f"{ADMIN_URL}/admin/routes/final-comprehensive-test", timeout=10)
    if delete_resp.status_code == 200:
        print_success("测试路由清理成功")
    
    return detail_resp.status_code == 200

def test_all_new_endpoints():
    """测试所有新增端点"""
    print("🚀 最终完整测试 - 所有新增管理接口")
    print("=" * 60)
    
    tests = [
        ("配置版本接口", test_config_version),
        ("事件统计接口", test_event_stats),
        ("事件流信息", test_event_stream_info),
        ("事件消费者", test_event_consumers),
        ("手动同步", test_manual_sync),
        ("事件清理", test_event_cleanup),
        ("路由详情", test_route_details),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 最终测试结果总结")
    print("=" * 60)
    
    successful_tests = [name for name, success in results if success]
    failed_tests = [name for name, success in results if not success]
    
    print(f"✅ 成功的测试 ({len(successful_tests)}):")
    for test_name in successful_tests:
        print(f"   - {test_name}")
    
    if failed_tests:
        print(f"❌ 失败的测试 ({len(failed_tests)}):")
        for test_name in failed_tests:
            print(f"   - {test_name}")
    else:
        print("🎉 所有测试全部通过！")
    
    success_rate = len(successful_tests) / len(results) * 100
    print(f"\n🎯 总体成功率: {success_rate:.1f}%")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    all_success = test_all_new_endpoints()
    
    if all_success:
        print("\n" + "🎊" * 20)
        print("🎉 恭喜！所有新增管理接口完全正常工作！")
        print("🎊" * 20)
        
        print("\n📋 现在可用的新管理功能:")
        print("   1. 实时配置版本监控")
        print("   2. 事件系统状态统计") 
        print("   3. 事件流详细信息")
        print("   4. 消费者状态监控")
        print("   5. 手动配置同步触发")
        print("   6. 事件数据清理")
        print("   7. 路由详情深度查询")
    else:
        print("\n⚠️ 部分功能需要进一步调试")
