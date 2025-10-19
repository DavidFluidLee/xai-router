#!/usr/bin/env python3
"""
测试增量同步性能
"""

import requests
import time
import statistics

BASE_URL = "http://localhost:8080"

def test_sync_performance():
    """测试同步性能"""
    print("🧪 测试同步性能...")
    
    sync_times = []
    
    for i in range(5):
        print(f"第 {i+1} 次同步测试...")
        
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/admin/sync/trigger")
        end_time = time.time()
        
        if response.status_code == 200:
            sync_time = (end_time - start_time) * 1000  # 转换为毫秒
            sync_times.append(sync_time)
            data = response.json()
            print(f"   耗时: {sync_time:.2f}ms (API返回: {data.get('duration_ms')}ms)")
        else:
            print(f"   同步失败: {response.text}")
        
        time.sleep(1)  # 等待1秒
    
    if sync_times:
        avg_time = statistics.mean(sync_times)
        min_time = min(sync_times)
        max_time = max(sync_times)
        
        print(f"\n📊 同步性能统计:")
        print(f"   平均耗时: {avg_time:.2f}ms")
        print(f"   最小耗时: {min_time:.2f}ms") 
        print(f"   最大耗时: {max_time:.2f}ms")
        print(f"   测试次数: {len(sync_times)}")

def test_route_operations_performance():
    """测试路由操作性能"""
    print("\n🧪 测试路由操作性能...")
    
    operation_times = []
    
    for i in range(10):
        route_id = f"perf-test-{i}"
        route_data = {
            "id": route_id,
            "path": f"/api/perf-{i}",
            "method": "GET",
            "handler": "sandbox",
            "sandbox_type": "python",
            "code": "print('Performance test')",
            "timeout": 5
        }
        
        # 测试创建性能
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/admin/routes", json=route_data)
        end_time = time.time()
        
        if response.status_code in [200, 201]:
            operation_time = (end_time - start_time) * 1000
            operation_times.append(operation_time)
            print(f"   创建路由 {route_id}: {operation_time:.2f}ms")
        else:
            print(f"   创建失败: {response.text}")
    
    if operation_times:
        avg_time = statistics.mean(operation_times)
        print(f"\n📊 路由创建性能:")
        print(f"   平均耗时: {avg_time:.2f}ms")
        print(f"   总路由数: {len(operation_times)}")
        
        # 清理测试路由
        for i in range(10):
            route_id = f"perf-test-{i}"
            requests.delete(f"{BASE_URL}/admin/routes/{route_id}")

def test_memory_usage():
    """测试内存使用情况"""
    print("\n🧪 测试内存使用情况...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/config/version")
        if response.status_code == 200:
            data = response.json()
            memory_routes = data.get('memory_routes', 0)
            total_routes = data.get('total_routes', 0)
            
            print(f"📊 内存使用统计:")
            print(f"   内存中路由数: {memory_routes}")
            print(f"   Redis中路由数: {total_routes}")
            print(f"   内存效率: {memory_routes}/{total_routes} ({memory_routes/total_routes*100 if total_routes > 0 else 0:.1f}%)")
            
    except Exception as e:
        print(f"❌ 内存测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始性能测试")
    print("=" * 50)
    
    test_sync_performance()
    test_route_operations_performance() 
    test_memory_usage()
    
    print("\n" + "=" * 50)
    print("🎯 性能测试完成")
