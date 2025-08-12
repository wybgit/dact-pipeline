# 执行引擎 API

执行引擎负责工具的实际执行、结果收集和验证。

## 执行器

### Executor 类

```{eval-rst}
.. autoclass:: dact.executor.Executor
   :members:
   :undoc-members:
   :show-inheritance:
```

## Pytest 集成

### TestCaseItem 类

```{eval-rst}
.. autoclass:: dact.pytest_plugin.TestCaseItem
   :members:
   :undoc-members:
   :show-inheritance:
```

### CaseYAMLFile 类

```{eval-rst}
.. autoclass:: dact.pytest_plugin.CaseYAMLFile
   :members:
   :undoc-members:
   :show-inheritance:
```

## 执行函数

### 场景执行

```{eval-rst}
.. autofunction:: dact.pytest_plugin.execute_scenario
```

### 工具执行

```{eval-rst}
.. autofunction:: dact.pytest_plugin.execute_tool
```

### 结果验证

```{eval-rst}
.. autofunction:: dact.pytest_plugin.validate_case_result
```

## 工作目录管理

### 目录管理函数

```{eval-rst}
.. autofunction:: dact.executor.setup_work_directory
```

```{eval-rst}
.. autofunction:: dact.executor.cleanup_work_directory
```

## 使用示例

### 直接执行工具

```python
from dact.executor import Executor
from dact.tool_loader import load_tool_from_file
from pathlib import Path

# 加载工具
tool = load_tool_from_file("tools/ai-json-operator.tool.yml")

# 创建执行器
executor = Executor(tool=tool)

# 设置工作目录
work_dir = Path("tmp/direct_execution")
work_dir.mkdir(parents=True, exist_ok=True)

# 执行工具
result = executor.execute(work_dir)

print(f"执行结果:")
print(f"  退出码: {result['returncode']}")
print(f"  执行时间: {result['execution_time']:.2f}秒")
print(f"  标准输出: {result['stdout'][:100]}...")

# 检查输出文件
if result.get('outputs'):
    print(f"  输出文件: {result['outputs']}")
```

### 执行场景

```python
from dact.pytest_plugin import execute_scenario
from dact.scenario_loader import load_scenario_from_file
from pathlib import Path

# 加载场景
scenario = load_scenario_from_file("scenarios/onnx-to-atc.scenario.yml")

# 设置参数
case_params = {
    "ops": "Conv Add",
    "soc_version": "Ascend310",
    "output_dir": "outputs/test"
}

# 执行场景
work_dir = Path("tmp/scenario_execution")
result = execute_scenario(scenario, case_params, work_dir)

print(f"场景执行结果: {result.status}")
print(f"总执行时间: {result.execution_time:.2f}秒")

# 查看各步骤结果
for step_name, step_result in result.step_results.items():
    print(f"步骤 {step_name}:")
    print(f"  状态: {step_result.status}")
    print(f"  退出码: {step_result.exit_code}")
    print(f"  执行时间: {step_result.execution_time:.2f}秒")
```

### 自定义验证器

```python
from dact.models import CaseValidation
import os

def validate_file_size(target: str, min_value: int, max_value: int = None) -> bool:
    """验证文件大小"""
    if not os.path.exists(target):
        return False
    
    file_size = os.path.getsize(target)
    if file_size < min_value:
        return False
    
    if max_value and file_size > max_value:
        return False
    
    return True

def validate_model_format(model_file: str, expected_format: str) -> bool:
    """验证模型格式"""
    # 实现模型格式验证逻辑
    if expected_format == "onnx":
        return model_file.endswith(".onnx")
    elif expected_format == "om":
        return model_file.endswith(".om")
    return False

# 注册自定义验证器
from dact.validation_engine import VALIDATION_FUNCTIONS
VALIDATION_FUNCTIONS["file_size"] = validate_file_size
VALIDATION_FUNCTIONS["model_format"] = validate_model_format
```

### 工作目录管理

```python
from dact.executor import setup_work_directory, cleanup_work_directory
from pathlib import Path

# 设置工作目录
case_name = "test_conv_add"
work_dir = setup_work_directory(case_name)

print(f"工作目录: {work_dir}")

# 创建步骤子目录
step_dir = work_dir / "generate_onnx"
step_dir.mkdir(exist_ok=True)

# 执行完成后清理（可选）
# cleanup_work_directory(work_dir, preserve_logs=True)
```

### 结果收集和报告

```python
from dact.executor import Executor
import json

class CustomExecutor(Executor):
    """自定义执行器，增加结果收集功能"""
    
    def execute(self, work_dir):
        # 调用父类执行方法
        result = super().execute(work_dir)
        
        # 收集额外的执行信息
        result['custom_metrics'] = {
            'cpu_usage': self._get_cpu_usage(),
            'memory_usage': self._get_memory_usage(),
            'disk_usage': self._get_disk_usage()
        }
        
        # 保存详细结果到文件
        result_file = work_dir / "execution_result.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        return result
    
    def _get_cpu_usage(self):
        # 实现CPU使用率获取
        return 0.0
    
    def _get_memory_usage(self):
        # 实现内存使用量获取
        return 0
    
    def _get_disk_usage(self):
        # 实现磁盘使用量获取
        return 0
```

### 并行执行

```python
import concurrent.futures
from dact.executor import Executor

def execute_tool_parallel(tool_configs, params_list):
    """并行执行多个工具"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # 提交执行任务
        future_to_config = {}
        for i, (tool_config, params) in enumerate(zip(tool_configs, params_list)):
            work_dir = Path(f"tmp/parallel_execution_{i}")
            executor_instance = Executor(tool=tool_config)
            future = executor.submit(executor_instance.execute, work_dir)
            future_to_config[future] = (tool_config.name, params)
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_config):
            tool_name, params = future_to_config[future]
            try:
                result = future.result()
                results.append({
                    'tool': tool_name,
                    'params': params,
                    'result': result
                })
            except Exception as e:
                results.append({
                    'tool': tool_name,
                    'params': params,
                    'error': str(e)
                })
    
    return results
```