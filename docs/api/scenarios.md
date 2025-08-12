# 场景管理 API

场景管理模块提供了场景的加载、验证和执行编排功能。

## 场景加载器

### ScenarioLoader 类

```{eval-rst}
.. autoclass:: dact.scenario_loader.ScenarioLoader
   :members:
   :undoc-members:
   :show-inheritance:
```

### 场景加载函数

```{eval-rst}
.. autofunction:: dact.scenario_loader.load_scenarios_from_directory
```

```{eval-rst}
.. autofunction:: dact.scenario_loader.load_scenario_from_file
```

## 依赖解析器

### DependencyResolver 类

```{eval-rst}
.. autoclass:: dact.dependency_resolver.DependencyResolver
   :members:
   :undoc-members:
   :show-inheritance:
```

## 参数渲染

### 模板渲染函数

```{eval-rst}
.. autofunction:: dact.scenario_loader.render_template
```

```{eval-rst}
.. autofunction:: dact.scenario_loader.render_step_params
```

## 使用示例

### 加载场景

```python
from dact.scenario_loader import load_scenarios_from_directory

# 从目录加载所有场景
scenarios = load_scenarios_from_directory("scenarios")

# 获取特定场景
e2e_scenario = scenarios.get("e2e-onnx-to-atc")
if e2e_scenario:
    print(f"场景名称: {e2e_scenario.name}")
    print(f"场景描述: {e2e_scenario.description}")
    print(f"步骤数量: {len(e2e_scenario.steps)}")
```

### 解析依赖关系

```python
from dact.dependency_resolver import DependencyResolver

# 创建依赖解析器
resolver = DependencyResolver()

# 解析执行顺序
execution_order = resolver.resolve_execution_order(e2e_scenario.steps)

print("执行顺序:")
for i, step_group in enumerate(execution_order):
    step_names = [step.name for step in step_group]
    print(f"  阶段 {i+1}: {', '.join(step_names)}")
```

### 参数渲染

```python
from dact.scenario_loader import render_step_params

# 模拟运行上下文
run_context = {
    "steps": {
        "generate_onnx": {
            "outputs": {
                "onnx_file": "outputs/model.onnx"
            }
        }
    },
    "params": {
        "soc_version": "Ascend310"
    }
}

# 渲染步骤参数
step_params = {
    "model": "{{ steps.generate_onnx.outputs.onnx_file }}",
    "soc_version": "{{ soc_version }}"
}

rendered_params = render_step_params(step_params, run_context)
print(f"渲染后的参数: {rendered_params}")
# 输出: {'model': 'outputs/model.onnx', 'soc_version': 'Ascend310'}
```

### 验证场景配置

```python
from dact.scenario_loader import load_scenario_from_file

try:
    # 加载并验证场景配置
    scenario = load_scenario_from_file("scenarios/my-scenario.scenario.yml")
    print(f"场景 {scenario.name} 加载成功")
    
    # 检查步骤依赖
    for step in scenario.steps:
        if step.depends_on:
            print(f"步骤 {step.name} 依赖于: {', '.join(step.depends_on)}")
            
except Exception as e:
    print(f"场景加载失败: {e}")
```

### 场景执行编排

```python
from dact.pytest_plugin import execute_scenario

# 执行场景
result = execute_scenario(
    scenario=e2e_scenario,
    case_params={"ops": "Conv Add", "soc_version": "Ascend310"},
    work_dir=Path("tmp/test_scenario")
)

print(f"场景执行结果: {result.status}")
print(f"执行时间: {result.execution_time}")

# 查看各步骤结果
for step_name, step_result in result.step_results.items():
    print(f"步骤 {step_name}: {step_result.status}")
```

### 自定义场景验证

```python
from dact.models import Scenario, Step

def validate_scenario_structure(scenario: Scenario) -> list:
    """验证场景结构"""
    errors = []
    
    # 检查步骤名称唯一性
    step_names = [step.name for step in scenario.steps]
    if len(step_names) != len(set(step_names)):
        errors.append("步骤名称不唯一")
    
    # 检查依赖关系
    for step in scenario.steps:
        if step.depends_on:
            for dep in step.depends_on:
                if dep not in step_names:
                    errors.append(f"步骤 {step.name} 依赖的步骤 {dep} 不存在")
    
    return errors

# 使用验证函数
errors = validate_scenario_structure(e2e_scenario)
if errors:
    print("场景验证失败:")
    for error in errors:
        print(f"  - {error}")
else:
    print("场景验证通过")
```