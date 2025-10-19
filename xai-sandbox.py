import json
import re
import base64
import requests
import httpx
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, StrEnum
from threading import Lock
from typing import Any, Dict, Tuple, List, Optional
from textwrap import dedent
from pydantic import BaseModel
from yarl import URL
import logging
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SandboxClient")

class CodeLanguage(StrEnum):
    """代码语言枚举"""
    PYTHON3 = "python3"

class CodeExecutionError(Exception):
    """代码执行错误"""
    pass

class CodeExecutionResponse(BaseModel):
    """代码执行响应"""

    class Data(BaseModel):
        stdout: str | None = None
        error: str | None = None

    code: int
    message: str
    data: Data

class TemplateTransformer(ABC):
    """模板转换器基类"""
    _code_placeholder: str = "{{code}}"
    _inputs_placeholder: str = "{{inputs}}"
    _result_tag: str = "<<RESULT>>"

    @classmethod
    def transform_caller(cls, code: str, inputs: Mapping[str, Any]) -> Tuple[str, str]:
        """
        转换代码为运行器脚本
        """
        runner_script = cls.assemble_runner_script(code, inputs)
        preload_script = cls.get_preload_script()
        return runner_script, preload_script

    @classmethod
    def extract_result_str_from_response(cls, response: str) -> str:
        """从响应中提取结果字符串"""
        result = re.search(rf"{cls._result_tag}(.*){cls._result_tag}", response, re.DOTALL)
        if not result:
            raise ValueError(f"Failed to parse result: no result tag found in response. Response: {response[:200]}...")
        return result.group(1)

    @classmethod
    def transform_response(cls, response: str) -> Mapping[str, Any]:
        """转换响应为字典"""
        try:
            result_str = cls.extract_result_str_from_response(response)
            result = json.loads(result_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}.")
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Unexpected error during response transformation: {str(e)}")

        if not isinstance(result, dict):
            raise ValueError(f"Result must be a dict, got {type(result).__name__}")
        if not all(isinstance(k, str) for k in result):
            raise ValueError("Result keys must be strings")

        return result

    @classmethod
    @abstractmethod
    def get_runner_script(cls) -> str:
        """获取运行器脚本"""
        pass

    @classmethod
    def serialize_inputs(cls, inputs: Mapping[str, Any]) -> str:
        """序列化输入参数"""
        inputs_json_str = json.dumps(inputs, ensure_ascii=False).encode()
        input_base64_encoded = base64.b64encode(inputs_json_str).decode("utf-8")
        return input_base64_encoded

    @classmethod
    def assemble_runner_script(cls, code: str, inputs: Mapping[str, Any]) -> str:
        """组装运行器脚本"""
        script = cls.get_runner_script()
        script = script.replace(cls._code_placeholder, code)
        inputs_str = cls.serialize_inputs(inputs)
        script = script.replace(cls._inputs_placeholder, inputs_str)
        return script

    @classmethod
    def get_preload_script(cls) -> str:
        """获取预加载脚本"""
        return ""

class Python3TemplateTransformer(TemplateTransformer):
    """Python3 模板转换器"""

    @classmethod
    def get_runner_script(cls) -> str:
        runner_script = dedent(f"""
            # declare main function
            {cls._code_placeholder}

            import json
            from base64 import b64decode

            # decode and prepare input dict
            inputs_obj = json.loads(b64decode('{cls._inputs_placeholder}').decode('utf-8'))

            # execute main function
            output_obj = main(**inputs_obj)

            # convert output to json and print
            output_json = json.dumps(output_obj, indent=4)
            result = f'''<<RESULT>>{{output_json}}<<RESULT>>'''
            print(result)
            """)
        return runner_script

class CodeExecutor:
    """
    完整的代码执行器
    支持函数执行、网络访问、数据处理等完整功能
    """

    # 代码模板转换器映射
    code_template_transformers: Dict[CodeLanguage, type[TemplateTransformer]] = {
        CodeLanguage.PYTHON3: Python3TemplateTransformer,
    }

    def __init__(self,
                 endpoint: str = "http://localhost:8194/v1/sandbox/run",
                 api_key: str = "dify-sandbox",
                 connect_timeout: int = 30,
                 read_timeout: int = 60,
                 write_timeout: int = 60,
                 enable_network: bool = True):
        """
        初始化代码执行器

        Args:
            endpoint: 沙箱端点URL
            api_key: API密钥
            connect_timeout: 连接超时（秒）
            read_timeout: 读取超时（秒）
            write_timeout: 写入超时（秒）
            enable_network: 是否启用网络访问
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.enable_network = enable_network

        # HTTP客户端配置
        self._client_limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=300,
        )

        # 创建HTTP客户端
        self._client = self._build_http_client()

    def _build_http_client(self) -> httpx.Client:
        """构建HTTP客户端"""
        return httpx.Client(
            verify=True,
            limits=self._client_limits,
        )

    def execute_code(self,
                     language: CodeLanguage,
                     preload: str,
                     code: str,
                     timeout: int = 10) -> str:
        """
        执行代码

        Args:
            language: 代码语言
            preload: 预加载脚本
            code: 要执行的代码
            timeout: 代码执行超时时间（秒）

        Returns:
            标准输出内容
        """
        headers = {"X-Api-Key": self.api_key}

        data = {
            "language": "python3",
            "code": code,
            "preload": preload,
            "enable_network": self.enable_network,
            "timeout": timeout,
        }

        # 配置请求超时
        request_timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=None,
        )

        try:
            response = self._client.post(
                self.endpoint,
                json=data,
                headers=headers,
                timeout=request_timeout,
            )

            if response.status_code == 503:
                raise CodeExecutionError("Code execution service is unavailable")
            elif response.status_code != 200:
                raise CodeExecutionError(
                    f"Failed to execute code, got status code {response.status_code},"
                    f" please check if the sandbox service is running"
                )
        except CodeExecutionError as e:
            raise e
        except Exception as e:
            raise CodeExecutionError(
                "Failed to execute code, which is likely a network issue,"
                " please check if the sandbox service is running."
                f" ( Error: {str(e)} )"
            )

        try:
            response_data = response.json()
        except Exception as e:
            raise CodeExecutionError("Failed to parse response") from e

        if (code := response_data.get("code")) != 0:
            raise CodeExecutionError(f"Got error code: {code}. Got error msg: {response_data.get('message')}")

        # 使用Pydantic模型验证响应
        response_obj = CodeExecutionResponse(**response_data)

        if response_obj.data.error:
            raise CodeExecutionError(response_obj.data.error)

        return response_obj.data.stdout or ""

    def execute_function(self,
                         code: str,
                         inputs: Mapping[str, Any],
                         timeout: int = 10) -> Mapping[str, Any]:
        """
        执行函数代码

        Args:
            code: 包含main函数的代码
            inputs: 函数输入参数
            timeout: 执行超时时间（秒）

        Returns:
            函数执行结果
        """
        template_transformer = self.code_template_transformers.get(CodeLanguage.PYTHON3)
        if not template_transformer:
            raise CodeExecutionError("Unsupported language")

        runner, preload = template_transformer.transform_caller(code, inputs)

        try:
            response = self.execute_code(CodeLanguage.PYTHON3, preload, runner, timeout=timeout)
        except CodeExecutionError as e:
            raise e

        return template_transformer.transform_response(response)

    def execute_simple_code(self, code: str, timeout: int = 10) -> str:
        """
        执行简单代码（不经过模板转换）

        Args:
            code: 要执行的代码
            timeout: 执行超时时间（秒）

        Returns:
            标准输出内容
        """
        return self.execute_code(CodeLanguage.PYTHON3, "", code, timeout)

    def test_connection(self) -> bool:
        """
        测试沙箱连接

        Returns:
            连接是否成功
        """
        try:
            result = self.execute_simple_code('print("Connection test")', timeout=5)
            return "Connection test" in result
        except CodeExecutionError:
            return False

    def close(self):
        """关闭HTTP客户端"""
        if hasattr(self, '_client') and self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# 预定义函数模板
class CodeTemplates:
    """代码模板集合"""

    @staticmethod
    def math_calculator() -> str:
        """数学计算器模板"""
        return """
def main(numbers: list, operations: list):
    results = {}

    for op in operations:
        if op == "sum":
            results["sum"] = sum(numbers)
        elif op == "average":
            results["average"] = sum(numbers) / len(numbers)
        elif op == "max":
            results["max"] = max(numbers)
        elif op == "min":
            results["min"] = min(numbers)
        elif op == "product":
            product = 1
            for num in numbers:
                product *= num
            results["product"] = product

    results["count"] = len(numbers)
    results["numbers"] = numbers
    return results
"""

    @staticmethod
    def data_analyzer() -> str:
        """数据分析器模板"""
        return """
def main(dataset: dict):
    data = dataset.get("data", [])
    analysis_type = dataset.get("analysis_type", "basic")

    results = {
        "data_count": len(data),
        "analysis_type": analysis_type
    }

    if data:
        if analysis_type == "basic":
            results.update({
                "sum": sum(data),
                "mean": sum(data) / len(data),
                "max": max(data),
                "min": min(data)
            })
        elif analysis_type == "statistical":
            import math
            mean = sum(data) / len(data)
            variance = sum((x - mean) ** 2 for x in data) / len(data)
            results.update({
                "mean": mean,
                "variance": variance,
                "std_dev": math.sqrt(variance),
                "range": max(data) - min(data)
            })

    return results
"""

    @staticmethod
    def network_tester() -> str:
        """网络测试器模板"""
        return """
import urllib.request
import socket
import time

def main(config: dict):
    results = {
        "dns_tests": {},
        "http_tests": {},
        "performance": {}
    }

    # DNS测试
    domains = config.get("domains", [])
    for domain in domains:
        try:
            start_time = time.time()
            ip = socket.gethostbyname(domain)
            resolve_time = (time.time() - start_time) * 1000
            results["dns_tests"][domain] = {
                "ip": ip,
                "resolve_time_ms": round(resolve_time, 2),
                "success": True
            }
        except Exception as e:
            results["dns_tests"][domain] = {
                "ip": "unknown",
                "error": str(e),
                "success": False
            }

    # HTTP测试
    websites = config.get("websites", [])
    for website in websites:
        try:
            start_time = time.time()
            response = urllib.request.urlopen(website, timeout=10)
            response_time = (time.time() - start_time) * 1000
            results["http_tests"][website] = {
                "status": response.status,
                "response_time_ms": round(response_time, 2),
                "success": True
            }
        except Exception as e:
            results["http_tests"][website] = {
                "status": "error",
                "error": str(e),
                "success": False
            }

    # 性能统计
    successful_dns = sum(1 for r in results["dns_tests"].values() if r["success"])
    successful_http = sum(1 for r in results["http_tests"].values() if r["success"])

    results["performance"] = {
        "dns_success_rate": successful_dns / len(domains) if domains else 0,
        "http_success_rate": successful_http / len(websites) if websites else 0,
        "total_tests": len(domains) + len(websites)
    }

    return results
"""

    @staticmethod
    def order_analyzer() -> str:
        """订单分析器模板 - 修复版本"""
        return """
def main(orders: list, date_filter: str = None, min_amount: float = 0):
    # 过滤订单
    filtered_orders = []
    total_revenue = 0

    for order in orders:
        order_date = order.get("date", "")
        amount = order.get("amount", 0)

        # 应用过滤条件
        if amount >= min_amount:
            if not date_filter or order_date >= date_filter:
                filtered_orders.append(order)
                total_revenue += amount

    # 计算统计
    avg_order_value = total_revenue / len(filtered_orders) if filtered_orders else 0

    return {
        "total_orders": len(orders),
        "filtered_orders": len(filtered_orders),
        "total_revenue": round(total_revenue, 2),
        "average_order_value": round(avg_order_value, 2),
        "filter_criteria": {
            "date_filter": date_filter,
            "min_amount": min_amount
        },
        "order_summary": [
            {
                "id": order.get("id"),
                "date": order.get("date"),
                "amount": order.get("amount"),
                "customer": order.get("customer")
            }
            for order in filtered_orders[:5]  # 只显示前5个订单
        ]
    }
"""

# 沙箱路由和客户端实现
class SandboxHealth(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class SandboxEndpoint:
    """沙箱端点配置"""
    name: str
    endpoint: str
    api_key: str
    weight: int = 1  # 负载权重
    enabled: bool = True
    last_health_check: float = 0
    health: SandboxHealth = SandboxHealth.UNKNOWN
    failure_count: int = 0
    success_count: int = 0

class SandboxRouter:
    """
    沙箱路由管理器
    支持负载均衡、健康检查、故障转移
    """
    
    def __init__(self, check_interval: int = 60):
        """
        初始化路由管理器
        
        Args:
            check_interval: 健康检查间隔（秒）
        """
        self.endpoints: Dict[str, SandboxEndpoint] = {}
        self.check_interval = check_interval
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=5)
        
    def add_endpoint(self, name: str, endpoint: str, api_key: str, weight: int = 1, enabled: bool = True):
        """添加沙箱端点"""
        with self._lock:
            self.endpoints[name] = SandboxEndpoint(
                name=name,
                endpoint=endpoint,
                api_key=api_key,
                weight=weight,
                enabled=enabled,
                last_health_check=0,
                health=SandboxHealth.UNKNOWN
            )
        logger.info(f"Added sandbox endpoint: {name} -> {endpoint}")
    
    def remove_endpoint(self, name: str):
        """移除沙箱端点"""
        with self._lock:
            if name in self.endpoints:
                del self.endpoints[name]
                logger.info(f"Removed sandbox endpoint: {name}")
    
    def enable_endpoint(self, name: str):
        """启用端点"""
        with self._lock:
            if name in self.endpoints:
                self.endpoints[name].enabled = True
                logger.info(f"Enabled sandbox endpoint: {name}")
    
    def disable_endpoint(self, name: str):
        """禁用端点"""
        with self._lock:
            if name in self.endpoints:
                self.endpoints[name].enabled = False
                logger.info(f"Disabled sandbox endpoint: {name}")
    
    def get_healthy_endpoints(self) -> List[SandboxEndpoint]:
        """获取健康的端点列表"""
        with self._lock:
            healthy_endpoints = [
                endpoint for endpoint in self.endpoints.values()
                if endpoint.enabled and endpoint.health == SandboxHealth.HEALTHY
            ]
            
            # 按权重排序（权重高的在前）
            healthy_endpoints.sort(key=lambda x: x.weight, reverse=True)
            return healthy_endpoints
    
    def select_endpoint(self) -> Optional[SandboxEndpoint]:
        """选择最优端点（基于权重和健康状态）"""
        healthy_endpoints = self.get_healthy_endpoints()
        if not healthy_endpoints:
            return None
        
        # 简单的权重选择（可以改进为更复杂的负载均衡算法）
        return healthy_endpoints[0]
    
    def health_check(self, endpoint: SandboxEndpoint) -> bool:
        """执行健康检查"""
        try:
            # 使用简单的代码执行来测试端点
            executor = CodeExecutor(
                endpoint=endpoint.endpoint,
                api_key=endpoint.api_key,
                connect_timeout=5,
                read_timeout=10,
                enable_network=False  # 健康检查时不使用网络
            )
            
            result = executor.test_connection()
            executor.close()
            
            return result
        except Exception as e:
            logger.warning(f"Health check failed for {endpoint.name}: {e}")
            return False
    
    def run_health_checks(self):
        """运行所有端点的健康检查"""
        current_time = time.time()
        
        with self._lock:
            endpoints_to_check = [
                endpoint for endpoint in self.endpoints.values()
                if endpoint.enabled and 
                (current_time - endpoint.last_health_check) > self.check_interval
            ]
        
        # 并行执行健康检查
        futures = {}
        for endpoint in endpoints_to_check:
            future = self._executor.submit(self.health_check, endpoint)
            futures[future] = endpoint
        
        for future in as_completed(futures):
            endpoint = futures[future]
            try:
                is_healthy = future.result()
                
                with self._lock:
                    endpoint.last_health_check = time.time()
                    
                    if is_healthy:
                        endpoint.health = SandboxHealth.HEALTHY
                        endpoint.success_count += 1
                        endpoint.failure_count = 0
                        logger.debug(f"Health check passed for {endpoint.name}")
                    else:
                        endpoint.health = SandboxHealth.UNHEALTHY
                        endpoint.failure_count += 1
                        logger.warning(f"Health check failed for {endpoint.name} (failures: {endpoint.failure_count})")
                        
            except Exception as e:
                with self._lock:
                    endpoint.last_health_check = time.time()
                    endpoint.health = SandboxHealth.UNHEALTHY
                    endpoint.failure_count += 1
                    logger.error(f"Health check error for {endpoint.name}: {e}")
    
    def start_health_monitor(self):
        """启动健康监控后台线程"""
        def monitor_loop():
            while True:
                try:
                    self.run_health_checks()
                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(10)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Health monitor started")
    
    def get_status_report(self) -> Dict[str, Any]:
        """获取状态报告"""
        with self._lock:
            total_endpoints = len(self.endpoints)
            healthy_endpoints = len([e for e in self.endpoints.values() if e.health == SandboxHealth.HEALTHY])
            enabled_endpoints = len([e for e in self.endpoints.values() if e.enabled])
            
            endpoint_details = {}
            for name, endpoint in self.endpoints.items():
                endpoint_details[name] = {
                    "endpoint": endpoint.endpoint,
                    "enabled": endpoint.enabled,
                    "health": endpoint.health.value,
                    "weight": endpoint.weight,
                    "failure_count": endpoint.failure_count,
                    "success_count": endpoint.success_count,
                    "last_health_check": endpoint.last_health_check
                }
            
            return {
                "total_endpoints": total_endpoints,
                "healthy_endpoints": healthy_endpoints,
                "enabled_endpoints": enabled_endpoints,
                "health_ratio": healthy_endpoints / enabled_endpoints if enabled_endpoints else 0,
                "endpoints": endpoint_details
            }

class SandboxClient:
    """
    高级沙箱客户端
    支持多端点路由、负载均衡、故障转移
    """
    
    def __init__(self, router: SandboxRouter, retry_count: int = 3):
        """
        初始化沙箱客户端
        
        Args:
            router: 沙箱路由器
            retry_count: 重试次数
        """
        self.router = router
        self.retry_count = retry_count
        self._executors_cache: Dict[str, CodeExecutor] = {}
        
        # 启动健康监控
        self.router.start_health_monitor()
        
        # 初始健康检查
        self.router.run_health_checks()
    
    def _get_executor(self, endpoint: SandboxEndpoint) -> CodeExecutor:
        """获取或创建代码执行器实例"""
        cache_key = f"{endpoint.endpoint}_{endpoint.api_key}"
        
        if cache_key not in self._executors_cache:
            self._executors_cache[cache_key] = CodeExecutor(
                endpoint=endpoint.endpoint,
                api_key=endpoint.api_key,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=10,
                enable_network=True
            )
        
        return self._executors_cache[cache_key]
    
    def execute_with_retry(self, execute_func, *args, **kwargs) -> Any:
        """
        带重试的执行方法
        
        Args:
            execute_func: 执行函数
            *args, **kwargs: 执行参数
            
        Returns:
            执行结果
        """
        last_exception = None
        
        for attempt in range(self.retry_count + 1):
            endpoint = self.router.select_endpoint()
            
            if not endpoint:
                raise CodeExecutionError("No healthy sandbox endpoints available")
            
            try:
                executor = self._get_executor(endpoint)
                result = execute_func(executor, *args, **kwargs)
                
                # 记录成功
                with self.router._lock:
                    endpoint.success_count += 1
                
                logger.debug(f"Execution successful on {endpoint.name} (attempt {attempt + 1})")
                return result
                
            except CodeExecutionError as e:
                last_exception = e
                
                # 记录失败
                with self.router._lock:
                    endpoint.failure_count += 1
                    # 如果连续失败，暂时禁用
                    if endpoint.failure_count >= 3:
                        endpoint.enabled = False
                        logger.warning(f"Temporarily disabled {endpoint.name} due to consecutive failures")
                
                logger.warning(f"Execution failed on {endpoint.name} (attempt {attempt + 1}): {e}")
                
                # 立即进行健康检查
                self.router.run_health_checks()
                
                if attempt < self.retry_count:
                    logger.info(f"Retrying... ({attempt + 1}/{self.retry_count})")
                    time.sleep(1 * (attempt + 1))  # 指数退避
        
        # 所有重试都失败
        raise CodeExecutionError(f"All {self.retry_count + 1} attempts failed. Last error: {last_exception}")
    
    def execute_function(self, code: str, inputs: Mapping[str, Any], timeout: int = 10) -> Mapping[str, Any]:
        """执行函数（带重试和故障转移）"""
        def _execute(executor, code, inputs, timeout):
            return executor.execute_function(code, inputs, timeout)
        
        return self.execute_with_retry(_execute, code, inputs, timeout)
    
    def execute_simple_code(self, code: str, timeout: int = 10) -> str:
        """执行简单代码（带重试和故障转移）"""
        def _execute(executor, code, timeout):
            return executor.execute_simple_code(code, timeout)
        
        return self.execute_with_retry(_execute, code, timeout)
    
    def batch_execute(self, tasks: List[Dict]) -> List[Dict]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表，每个任务包含 code, inputs, timeout
            
        Returns:
            执行结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=min(len(tasks), 10)) as executor:
            future_to_task = {}
            
            for task in tasks:
                future = executor.submit(
                    self.execute_function,
                    task['code'],
                    task.get('inputs', {}),
                    task.get('timeout', 10)
                )
                future_to_task[future] = task
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append({
                        'task': task,
                        'success': True,
                        'result': result
                    })
                except Exception as e:
                    results.append({
                        'task': task,
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return self.router.get_status_report()
    
    def close(self):
        """关闭所有执行器"""
        for executor in self._executors_cache.values():
            executor.close()
        self._executors_cache.clear()

def main():
    """演示沙箱客户端的使用"""
    
    # 创建路由管理器
    router = SandboxRouter(check_interval=30)
    
    # 添加多个沙箱端点
    router.add_endpoint(
        name="primary",
        endpoint="https://xai.digiwincloud.com.cn/v1/sandbox/run",
        api_key="xai-sandbox",
        weight=10
    )
    
    router.add_endpoint(
        name="secondary",
        endpoint="https://backup-xai.digiwincloud.com.cn/v1/sandbox/run",
        api_key="xai-sandbox",
        weight=5
    )
    
    router.add_endpoint(
        name="local",
        endpoint="http://localhost:8194/v1/sandbox/run",
        api_key="dify-sandbox",
        weight=3
    )
    
    # 创建客户端
    client = SandboxClient(router, retry_count=2)
    
    try:
        # 显示初始状态
        print("🔧 沙箱客户端状态:")
        status = client.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 执行测试任务
        print("\n🚀 执行测试任务...")
        
        # 数学计算
        math_result = client.execute_function(
            CodeTemplates.math_calculator(),
            {
                "numbers": [1, 2, 3, 4, 5],
                "operations": ["sum", "average"]
            }
        )
        print(f"数学计算结果: {json.dumps(math_result, indent=2, ensure_ascii=False)}")
        
        # 批量执行
        print("\n📦 批量执行测试...")
        tasks = [
            {
                'code': CodeTemplates.math_calculator(),
                'inputs': {'numbers': [i, i+1, i+2], 'operations': ['sum']},
                'timeout': 5
            }
            for i in range(3)
        ]
        
        batch_results = client.batch_execute(tasks)
        for i, result in enumerate(batch_results):
            if result['success']:
                print(f"任务 {i+1}: 成功 - {result['result']}")
            else:
                print(f"任务 {i+1}: 失败 - {result['error']}")
        
        # 显示最终状态
        print("\n📊 最终状态:")
        final_status = client.get_status()
        print(json.dumps(final_status, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 执行错误: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
