# 验证引擎 API

验证引擎提供了多种验证规则和自定义验证功能。

## 验证引擎

### ValidationEngine 类

```{eval-rst}
.. autoclass:: dact.validation_engine.ValidationEngine
   :members:
   :undoc-members:
   :show-inheritance:
```

## 内置验证函数

### 基本验证

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_exit_code
```

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_stdout_contains
```

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_stderr_contains
```

### 文件验证

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_file_exists
```

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_file_size
```

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_directory_exists
```

### 性能验证

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_execution_time
```

```{eval-rst}
.. autofunction:: dact.validation_engine.validate_memory_usage
```

## 验证规则注册

### 注册自定义验证函数

```{eval-rst}
.. autofunction:: dact.validation_engine.register_validation_function
```

## 使用示例

### 基本验证

```python
from dact.validation_engine import ValidationEngine
from dact.models import CaseValidation

# 创建验证引擎
validator = ValidationEngine()

# 定义验证规则
validations = [
    CaseValidation(
        type="exit_code",
        expected=0,
        description="工具应该成功执行"
    ),
    CaseValidation(
        type="file_exists",
        target="outputs/**/*.onnx",
        description="应该生成ONNX文件"
    ),
    CaseValidation(
        type="file_size",
        target="outputs/model.om",
        min_value=1000,
        max_value=10000000,
        description="模型文件大小应在合理范围内"
    )
]

# 执行验证
execution_result = {
    "returncode": 0,
    "stdout": "Generation completed successfully",
    "stderr": "",
    "execution_time": 45.2
}

work_dir = Path("tmp/test_validation")
validation_results = validator.validate(validations, execution_result, work_dir)

# 检查验证结果
for result in validation_results:
    print(f"验证 {result.type}: {'通过' if result.passed else '失败'}")
    if not result.passed:
        print(f"  错误: {result.error_message}")
```

### 自定义验证函数

```python
from dact.validation_engine import register_validation_function
import json
import os

def validate_json_schema(target: str, schema: dict) -> tuple[bool, str]:
    """验证JSON文件是否符合指定模式"""
    try:
        if not os.path.exists(target):
            return False, f"文件 {target} 不存在"
        
        with open(target, 'r') as f:
            data = json.load(f)
        
        # 简单的模式验证示例
        for key, expected_type in schema.items():
            if key not in data:
                return False, f"缺少必需字段: {key}"
            
            if not isinstance(data[key], expected_type):
                return False, f"字段 {key} 类型错误，期望 {expected_type.__name__}"
        
        return True, "JSON模式验证通过"
        
    except Exception as e:
        return False, f"JSON验证失败: {str(e)}"

def validate_model_accuracy(model_file: str, test_data: str, threshold: float) -> tuple[bool, str]:
    """验证模型精度"""
    try:
        # 这里应该实现实际的模型精度验证逻辑
        # 示例：加载模型，运行测试数据，计算精度
        
        # 模拟精度计算
        accuracy = 0.96  # 实际应该从模型推理结果计算
        
        if accuracy >= threshold:
            return True, f"模型精度 {accuracy:.3f} 达到要求 (>= {threshold})"
        else:
            return False, f"模型精度 {accuracy:.3f} 未达到要求 (< {threshold})"
            
    except Exception as e:
        return False, f"精度验证失败: {str(e)}"

# 注册自定义验证函数
register_validation_function("json_schema", validate_json_schema)
register_validation_function("model_accuracy", validate_model_accuracy)
```

### 使用自定义验证

```python
# 在测试用例中使用自定义验证
validations = [
    CaseValidation(
        type="json_schema",
        target="outputs/metadata.json",
        params={
            "schema": {
                "model_name": str,
                "accuracy": float,
                "layers": int
            }
        },
        description="元数据应符合预期格式"
    ),
    CaseValidation(
        type="model_accuracy",
        target="outputs/model.om",
        params={
            "test_data": "test_data.bin",
            "threshold": 0.95
        },
        description="模型精度应达到95%"
    )
]

# 执行验证
validation_results = validator.validate(validations, execution_result, work_dir)
```

### 条件验证

```python
def validate_conditional(condition: str, validations: list) -> tuple[bool, str]:
    """条件验证：仅在满足条件时执行验证"""
    # 评估条件表达式
    if eval(condition):  # 注意：实际使用中应该使用更安全的表达式评估
        # 执行验证
        for validation in validations:
            passed, message = execute_validation(validation)
            if not passed:
                return False, message
        return True, "条件验证通过"
    else:
        return True, "条件不满足，跳过验证"

# 使用条件验证
conditional_validation = CaseValidation(
    type="conditional",
    params={
        "condition": "execution_result['returncode'] == 0",
        "validations": [
            {"type": "file_exists", "target": "outputs/*.om"},
            {"type": "file_size", "target": "outputs/*.om", "min_value": 1000}
        ]
    },
    description="仅在执行成功时验证输出文件"
)
```

### 批量验证

```python
def validate_batch_results(results: list, validations: list) -> dict:
    """批量验证多个执行结果"""
    batch_results = {
        "total": len(results),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    validator = ValidationEngine()
    
    for i, result in enumerate(results):
        work_dir = Path(f"tmp/batch_validation_{i}")
        validation_results = validator.validate(validations, result, work_dir)
        
        all_passed = all(vr.passed for vr in validation_results)
        if all_passed:
            batch_results["passed"] += 1
        else:
            batch_results["failed"] += 1
        
        batch_results["details"].append({
            "index": i,
            "passed": all_passed,
            "validations": [
                {
                    "type": vr.type,
                    "passed": vr.passed,
                    "message": vr.error_message if not vr.passed else "通过"
                }
                for vr in validation_results
            ]
        })
    
    return batch_results

# 使用批量验证
batch_validations = [
    CaseValidation(type="exit_code", expected=0),
    CaseValidation(type="file_exists", target="outputs/*.om")
]

batch_results = validate_batch_results(execution_results, batch_validations)
print(f"批量验证结果: {batch_results['passed']}/{batch_results['total']} 通过")
```

### 验证报告生成

```python
from datetime import datetime
import json

class ValidationReporter:
    """验证结果报告生成器"""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, case_name: str, validations: list, results: list):
        """添加验证结果"""
        self.results.append({
            "case_name": case_name,
            "timestamp": datetime.now().isoformat(),
            "validations": [
                {
                    "type": v.type,
                    "description": v.description,
                    "passed": r.passed,
                    "message": r.error_message if not r.passed else "通过"
                }
                for v, r in zip(validations, results)
            ]
        })
    
    def generate_html_report(self, output_file: str):
        """生成HTML验证报告"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>DACT Pipeline 验证报告</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .passed { color: green; }
                .failed { color: red; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>DACT Pipeline 验证报告</h1>
            <p>生成时间: {timestamp}</p>
            
            <h2>验证结果汇总</h2>
            <table>
                <tr>
                    <th>测试用例</th>
                    <th>验证项</th>
                    <th>结果</th>
                    <th>说明</th>
                </tr>
                {rows}
            </table>
        </body>
        </html>
        """
        
        rows = []
        for result in self.results:
            for validation in result["validations"]:
                status_class = "passed" if validation["passed"] else "failed"
                status_text = "通过" if validation["passed"] else "失败"
                
                rows.append(f"""
                <tr>
                    <td>{result["case_name"]}</td>
                    <td>{validation["description"]}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{validation["message"]}</td>
                </tr>
                """)
        
        html_content = html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            rows="".join(rows)
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_json_report(self, output_file: str):
        """生成JSON验证报告"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_cases": len(self.results),
                "total_validations": sum(len(r["validations"]) for r in self.results),
                "passed_validations": sum(
                    sum(1 for v in r["validations"] if v["passed"]) 
                    for r in self.results
                )
            },
            "results": self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

# 使用验证报告生成器
reporter = ValidationReporter()

# 添加验证结果
reporter.add_result("test_conv_add", validations, validation_results)

# 生成报告
reporter.generate_html_report("validation_report.html")
reporter.generate_json_report("validation_report.json")
```