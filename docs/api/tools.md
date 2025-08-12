# 工具管理 API

工具管理模块提供了工具的加载、验证和执行功能。

## 工具加载器

### ToolLoader 类

```{eval-rst}
.. autoclass:: dact.tool_loader.ToolLoader
   :members:
   :undoc-members:
   :show-inheritance:
```

### 工具加载函数

```{eval-rst}
.. autofunction:: dact.tool_loader.load_tools_from_directory
```

```{eval-rst}
.. autofunction:: dact.tool_loader.load_tool_from_file
```

## 工具执行器

### Executor 类

```{eval-rst}
.. autoclass:: dact.executor.Executor
   :members:
   :undoc-members:
   :show-inheritance:
```

### 后处理函数

DACT Pipeline 提供了一系列内置的后处理函数，用于从工具执行结果中提取信息。

```{eval-rst}
.. autofunction:: dact.executor.find_file
```

```{eval-rst}
.. autofunction:: dact.executor.find_latest_file
```

```{eval-rst}
.. autofunction:: dact.executor.find_onnx_file
```

```{eval-rst}
.. autofunction:: dact.executor.find_onnx_dir
```

```{eval-rst}
.. autofunction:: dact.executor.check_file_exists
```

## 使用示例

### 加载工具

```python
from dact.tool_loader import load_tools_from_directory

# 从目录加载所有工具
tools = load_tools_from_directory("tools")

# 获取特定工具
ai_tool = tools.get("ai-json-operator")
if ai_tool:
    print(f"工具名称: {ai_tool.name}")
    print(f"工具类型: {ai_tool.type}")
    print(f"命令模板: {ai_tool.command_template}")
```

### 执行工具

```python
from dact.executor import Executor
from pathlib import Path

# 创建执行器
executor = Executor(tool=ai_tool)

# 设置参数
params = {
    "ops": "Conv Add",
    "convert_to_onnx": True,
    "output_dir": "outputs"
}

# 执行工具
work_dir = Path("tmp/test_execution")
result = executor.execute(work_dir)

print(f"退出码: {result['returncode']}")
print(f"标准输出: {result['stdout']}")
print(f"执行时间: {result['execution_time']}")
```

### 自定义后处理函数

```python
import os
import glob

def find_model_file(dir: str, pattern: str = "**/*.model") -> str:
    """查找模型文件"""
    search_path = os.path.join(dir, pattern)
    files = glob.glob(search_path, recursive=True)
    if not files:
        raise FileNotFoundError(f"No model file found in {dir}")
    return max(files, key=os.path.getctime)

# 注册自定义函数
from dact.executor import POST_EXEC_FUNCTIONS
POST_EXEC_FUNCTIONS["find_model_file"] = find_model_file
```

### 工具验证

```python
from dact.tool_loader import load_tool_from_file

try:
    # 加载并验证工具配置
    tool = load_tool_from_file("tools/my-tool.tool.yml")
    print(f"工具 {tool.name} 加载成功")
except Exception as e:
    print(f"工具加载失败: {e}")
```