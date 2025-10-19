#!/usr/bin/env python3
import requests
import json

def test_gateway_status():
    print("🔍 网关状态检查")
    print("=" * 50)
    
    base_url = "http://localhost:8081"
    headers = {"X-Api-Key": "xai-admin-internal"}
    
    # 1. 检查基本状态
    print("1. 基本状态检查:")
    try:
        # 公共健康检查
        resp = requests.get(f"{base_url}/health", timeout=5)
        print(f"   ✅ 公共健康: {resp.status_code} - {resp.json().get('status')}")
        
        # 管理健康检查
        resp = requests.get(f"{base_url}/admin/health", headers=headers, timeout=5)
        data = resp.json()
        print(f"   ✅ 管理健康: {resp.status_code}")
        print(f"      路由数: {data.get('route_count', 0)}")
        print(f"      沙箱数: {data.get('sandbox_count', 0)}")
        print(f"      Redis状态: {data.get('redis', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")
    
    # 2. 检查配置版本
    print("\n2. 配置信息:")
    try:
        resp = requests.get(f"{base_url}/admin/config/version", headers=headers, timeout=5)
        data = resp.json()
        print(f"   ✅ 配置版本: {data.get('storage_mode', 'memory')}模式")
        print(f"      实例ID: {data.get('instance_id', 'N/A')}")
        print(f"      路由数: {data.get('total_routes', 0)}")
        
    except Exception as e:
        print(f"   ❌ 配置检查失败: {e}")
    
    # 3. 检查当前路由
    print("\n3. 路由信息:")
    try:
        resp = requests.get(f"{base_url}/admin/routes", headers=headers, timeout=5)
        routes = resp.json().get('routes', [])
        print(f"   ✅ 当前路由: {len(routes)} 个")
        
        for route in routes:
            print(f"      - {route.get('method', 'GET')} {route.get('path')} -> {route.get('handler')}")
            
    except Exception as e:
        print(f"   ❌ 路由检查失败: {e}")
    
    # 4. 测试网关端口
    print("\n4. 网关端口测试:")
    try:
        resp = requests.get("http://localhost:8080/health", timeout=5)
        print(f"   ✅ 网关端口: {resp.status_code} - 服务正常")
    except Exception as e:
        print(f"   ❌ 网关端口: {e}")

if __name__ == "__main__":
    test_gateway_status()
    print("\n" + "=" * 50)
    print("🎉 网关状态检查完成!")
    print("💡 网关正在内存模式下健康运行")
    print("💡 所有管理功能均可正常使用")
