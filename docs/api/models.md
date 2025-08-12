# 数据模型 API

DACT Pipeline 使用 Pydantic 定义了一系列数据模型来表示工具、场景、测试用例等核心概念。

## 核心模型

### Tool 模型

```{eval-rst}
.. autoclass:: dact.models.Tool
   :members:
   :undoc-members:
   :show-inheritance:
```

### ToolParameter 模型

```{eval-rst}
.. autoclass:: dact.models.ToolParameter
   :members:
   :undoc-members:
   :show-inheritance:
```

### PostExec 模型

```{eval-rst}
.. autoclass:: dact.models.PostExec
   :members:
   :undoc-members:
   :show-inheritance:
```

## 场景模型

### Scenario 模型

```{eval-rst}
.. autoclass:: dact.models.Scenario
   :members:
   :undoc-members:
   :show-inheritance:
```

### Step 模型

```{eval-rst}
.. autoclass:: dact.models.Step
   :members:
   :undoc-members:
   :show-inheritance:
```

## 测试用例模型

### Case 模型

```{eval-rst}
.. autoclass:: dact.models.Case
   :members:
   :undoc-members:
   :show-inheritance:
```

### CaseFile 模型

```{eval-rst}
.. autoclass:: dact.models.CaseFile
   :members:
   :undoc-members:
   :show-inheritance:
```

### CaseValidation 模型

```{eval-rst}
.. autoclass:: dact.models.CaseValidation
   :members:
   :undoc-members:
   :show-inheritance:
```

## 执行结果模型

### ExecutionResult 模型

```{eval-rst}
.. autoclass:: dact.models.ExecutionResult
   :members:
   :undoc-members:
   :show-inheritance:
```

### StepResult 模型

```{eval-rst}
.. autoclass:: dact.models.StepResult
   :members:
   :undoc-members:
   :show-inheritance:
```

## 使用示例

### 创建工具定义

```python
from dact.models import Tool, ToolParameter

# 定义工具参数
param = ToolParameter(
    type="str",
    required=True,
    help="输入文件路径"
)

# 创建工具定义
tool = Tool(
    name="my-tool",
    type="shell",
    description="我的自定义工具",
    command_template="my-tool --input {{ input_file }}",
    parameters={"input_file": param}
)
```

### 创建场景定义

```python
from dact.models import Scenario, Step

# 定义步骤
step1 = Step(
    name="process_data",
    tool="data-processor",
    params={"input": "data.txt"}
)

step2 = Step(
    name="analyze_results",
    tool="analyzer",
    depends_on=["process_data"],
    params={"input": "{{ steps.process_data.outputs.result }}"}
)

# 创建场景
scenario = Scenario(
    name="data-analysis",
    description="数据分析场景",
    steps=[step1, step2]
)
```

### 创建测试用例

```python
from dact.models import Case, CaseValidation

# 定义验证规则
validation = CaseValidation(
    type="exit_code",
    expected=0
)

# 创建测试用例
case = Case(
    name="test_data_analysis",
    description="数据分析测试",
    scenario="data-analysis",
    params={"input_file": "test_data.txt"},
    validation=[validation]
)
```