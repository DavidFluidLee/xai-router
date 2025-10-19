import json
import re
import base64
import requests
import httpx
from abc import ABC, abstractmethod
from collections.abc import Mapping
from enum import StrEnum
from threading import Lock
from typing import Any, Dict, Tuple, List, Optional
from textwrap import dedent
from pydantic import BaseModel
from yarl import URL


class CodeLanguage(StrEnum):
    """代码语言枚举"""
    PYTHON3 = "python3"


class CodeExecutionError(Exception):
    """代码执行错误"""
    pass


class CodeExecutionResponse(BaseModel):
    """代码执行响应 - 适配实际沙箱格式"""

    class Data(BaseModel):
        stdout: str | None = None
        error: str | None = None  # 沙箱返回的是空字符串或错误信息

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
        # 如果响应已经包含结果标签，直接提取
        result = re.search(rf"{cls._result_tag}(.*){cls._result_tag}", response, re.DOTALL)
        if result:
            return result.group(1)
        
        # 如果没有结果标签，尝试解析整个stdout作为JSON
        try:
            # 清理输出，移除可能的调试信息
            cleaned_response = response.strip()
            # 尝试直接解析为JSON
            json.loads(cleaned_response)
            return cleaned_response
        except json.JSONDecodeError:
            # 如果无法解析为JSON，返回原始响应
            return response

    @classmethod
    def transform_response(cls, response: str) -> Mapping[str, Any]:
        """转换响应为字典"""
        try:
            result_str = cls.extract_result_str_from_response(response)
            result = json.loads(result_str)
        except json.JSONDecodeError as e:
            # 如果JSON解析失败，返回原始字符串
            return {"raw_output": result_str, "error": f"JSON解析失败: {str(e)}"}
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"响应转换时发生意外错误: {str(e)}")

        if not isinstance(result, dict):
            return {"raw_output": result_str, "parsed_result": result}

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
            output_json = json.dumps(output_obj, indent=4, ensure_ascii=False)
            print(output_json)
            """)
        return runner_script


class SimplePython3TemplateTransformer(TemplateTransformer):
    """简化版Python3模板转换器 - 直接返回JSON结果"""
    
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

            # 直接返回JSON结果，不包装标签
            output_json = json.dumps(output_obj, ensure_ascii=False)
            print(output_json)
            """)
        return runner_script
    
    @classmethod
    def transform_response(cls, response: str) -> Mapping[str, Any]:
        """转换响应为字典 - 简化版本"""
        try:
            cleaned_response = response.strip()
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            # 如果解析失败，返回原始输出
            return {"raw_output": cleaned_response}


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
                 enable_network: bool = True,
                 use_simple_transformer: bool = True):
        """
        初始化代码执行器

        Args:
            endpoint: 沙箱端点URL
            api_key: API密钥
            connect_timeout: 连接超时（秒）
            read_timeout: 读取超时（秒）
            write_timeout: 写入超时（秒）
            enable_network: 是否启用网络访问
            use_simple_transformer: 是否使用简化模板转换器
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.enable_network = enable_network

        # 根据选择使用不同的模板转换器
        if use_simple_transformer:
            self.code_template_transformers[CodeLanguage.PYTHON3] = SimplePython3TemplateTransformer

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
            print(f"📤 发送请求到沙箱: {self.endpoint}")
            print(f"📝 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response = self._client.post(
                self.endpoint,
                json=data,
                headers=headers,
                timeout=request_timeout,
            )

            print(f"📥 收到响应: 状态码 {response.status_code}")
            
            if response.status_code == 503:
                raise CodeExecutionError("代码执行服务不可用")
            elif response.status_code != 200:
                raise CodeExecutionError(
                    f"代码执行失败，状态码 {response.status_code},"
                    f" 请检查沙箱服务是否正常运行"
                )
        except CodeExecutionError as e:
            raise e
        except Exception as e:
            raise CodeExecutionError(
                "代码执行失败，可能是网络问题，"
                f" 请检查沙箱服务是否正常运行。 (错误: {str(e)} )"
            )

        try:
            response_data = response.json()
            print(f"📋 响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        except Exception as e:
            raise CodeExecutionError(f"解析响应失败: {str(e)}") from e

        # 使用Pydantic模型验证响应
        try:
            response_obj = CodeExecutionResponse(**response_data)
        except Exception as e:
            raise CodeExecutionError(f"响应格式无效: {str(e)}")

        if response_obj.code != 0:
            raise CodeExecutionError(f"错误代码: {response_obj.code}. 错误信息: {response_obj.message}")

        # 检查错误字段（沙箱返回的是空字符串或错误信息）
        if response_obj.data.error and response_obj.data.error.strip():
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
            raise CodeExecutionError("不支持的语言")

        runner, preload = template_transformer.transform_caller(code, inputs)
        
        print(f"🔧 生成的运行器代码:")
        print(runner)

        try:
            response = self.execute_code(CodeLanguage.PYTHON3, preload, runner, timeout=timeout)
            print(f"📄 原始响应: {repr(response)}")
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
            print(f"🔗 连接测试结果: {repr(result)}")
            return "Connection test" in result
        except CodeExecutionError as e:
            print(f"🔗 连接测试失败: {e}")
            return False

    def close(self):
        """关闭HTTP客户端"""
        if hasattr(self, '_client') and self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 预定义函数模板 - 修复版本
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
    def simple_math() -> str:
        """简单数学计算模板"""
        return """
def main(a: float, b: float, operation: str = "add"):
    if operation == "add":
        return {"result": a + b}
    elif operation == "subtract":
        return {"result": a - b}
    elif operation == "multiply":
        return {"result": a * b}
    elif operation == "divide":
        if b == 0:
            return {"error": "除数不能为零"}
        return {"result": a / b}
    else:
        return {"error": f"不支持的操作: {operation}"}
"""


def test_sandbox_directly():
    """直接测试沙箱"""
    print("🧪 直接测试沙箱...")
    
    # 使用requests直接测试
    url = "https://xai.digiwincloud.com.cn/v1/sandbox/run"
    headers = {
        "X-Api-Key": "xai-sandbox",
        "Content-Type": "application/json"
    }
    
    # 测试简单代码
    data = {
        "language": "python3",
        "code": "print(1+1)",
        "preload": "",
        "enable_network": True,
        "timeout": 10
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"直接测试失败: {e}")


def main():
    """主函数演示"""

    print("🚀 完整功能代码执行器 - 修复版本")
    print("=" * 60)

    # 先直接测试沙箱
    test_sandbox_directly()

    # 创建代码执行器
    with CodeExecutor(
            endpoint="https://xai.digiwincloud.com.cn/v1/sandbox/run",
            api_key="xai-sandbox",
            connect_timeout=10,
            read_timeout=30,
            write_timeout=10,
            enable_network=True,
            use_simple_transformer=True  # 使用简化模板转换器
    ) as executor:

        # 测试连接
        print("\n🔧 测试沙箱连接...")
        if executor.test_connection():
            print("✅ 沙箱连接成功")
        else:
            print("❌ 沙箱连接失败")
            return

        print(f"\n📊 执行器配置:")
        print(f"   端点: {executor.endpoint}")
        print(f"   连接超时: {executor.connect_timeout}s")
        print(f"   读取超时: {executor.read_timeout}s")
        print(f"   启用网络: {executor.enable_network}")

        # 示例1: 简单数学计算
        print("\n1. 🧮 简单数学计算")
        math_inputs = {
            "a": 10,
            "b": 5,
            "operation": "add"
        }

        try:
            result = executor.execute_function(
                CodeTemplates.simple_math(),
                math_inputs,
                timeout=10
            )
            print(f"   输入: {math_inputs}")
            print(f"   结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        except CodeExecutionError as e:
            print(f"   ❌ 执行错误: {e}")

        # 示例2: 简单代码执行
        print("\n2. ⚡ 简单代码执行")
        try:
            result = executor.execute_simple_code("""
print("=== 简单代码测试 ===")
numbers = [1, 2, 3, 4, 5]
print(f"数字列表: {numbers}")
print(f"总和: {sum(numbers)}")
print(f"平均值: {sum(numbers) / len(numbers)}")
""", timeout=5)
            print(f"   输出: {result}")
        except CodeExecutionError as e:
            print(f"   ❌ 执行错误: {e}")

        print(f"\n🎉 测试完成！")


if __name__ == "__main__":
    main()
