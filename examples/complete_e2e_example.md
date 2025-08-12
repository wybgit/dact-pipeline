# 完整的端到端测试示例

本文档提供了一个完整的端到端测试示例，展示如何使用DACT Pipeline进行ONNX到ATC转换的完整测试流程。

## 示例概述

这个示例演示了：
- 完整的ONNX模型生成和ATC转换流程
- 动态文件名处理和参数传递
- 多层次的验证规则
- 错误处理和重试机制
- 数据驱动的批量测试

## 项目结构

```
examples/
├── tools/                          # 工具定义
│   ├── ai-json-operator.tool.yml   # ONNX生成工具
│   ├── atc.tool.yml                # ATC转换工具
│   └── file-validator.tool.yml     # 文件验证工具
├── scenarios/                      # 场景定义
│   └── onnx_to_atc.scenario.yml    # 端到端转换场景
├── cases/                          # 测试用例
│   ├── e2e_onnx_to_atc.case.yml    # 基础端到端测试
│   ├── comprehensive_e2e_validation.case.yml  # 全面验证测试
│   └── simple_e2e_integration.case.yml        # 简单集成测试
└── complete_e2e_example.md         # 本文档
```

## 步骤1: 工具定义

### AI JSON Operator 工具

```yaml
# tools/ai-json-operator.tool.yml
name: ai-json-operator
type: shell
description: "AI JSON Operator工具，用于生成ONNX模型"
command_template: 'ai-json-operator "{{ ops }}" {% if convert_to_onnx %}--convert-to-onnx{% endif %} --max-retries {{ max_retries }} -o {{ output_dir }}'

parameters:
  ops:
    type: str
    required: true
    help: "操作符列表，如 'Conv Add'"
  
  convert_to_onnx:
    type: bool
    required: false
    default: false
    help: "是否转换为ONNX格式"
  
  max_retries:
    type: int
    required: false
    default: 3
    help: "最大重试次数"
  
  output_dir:
    type: str
    required: false
    default: "outputs"
    help: "输出目录"

success_pattern: "Generation completed successfully"
failure_pattern: "Generation failed"
timeout: 300

post_exec:
  outputs:
    onnx_file: "find_onnx_file(dir='{{ output_dir }}')"
    onnx_dir: "find_onnx_dir(dir='{{ output_dir }}')"
```

### ATC 转换工具

```yaml
# tools/atc.tool.yml
name: atc
type: shell
description: "ATC模型转换工具"
command_template: 'atc --framework={{ framework }} --model={{ model }} --input_format={{ input_format }} --output={{ output }} --log={{ log }} --soc_version={{ soc_version }}'

parameters:
  framework:
    type: int
    required: true
    help: "框架类型，5表示ONNX"
  
  model:
    type: str
    required: true
    help: "ONNX模型文件路径"
  
  input_format:
    type: str
    required: false
    default: "NCHW"
    help: "输入数据格式"
  
  output:
    type: str
    required: true
    help: "输出文件路径"
  
  log:
    type: str
    required: false
    default: "info"
    help: "日志级别"
  
  soc_version:
    type: str
    required: true
    help: "SoC版本，如Ascend310"

success_pattern: "ATC run success"
failure_pattern: "ATC run failed"
timeout: 600

post_exec:
  outputs:
    om_file: "find_latest_file(dir='{{ output | dirname }}', pattern='*.om')"
    log_file: "find_latest_file(dir='{{ output | dirname }}', pattern='*.log')"
```

### 文件验证工具

```yaml
# tools/file-validator.tool.yml
name: file-validator
type: python
description: "文件验证工具"
python_module: "dact.validators.file_validator"

parameters:
  check_path:
    type: str
    required: true
    help: "要检查的文件或目录路径"
  
  expected_files:
    type: list
    required: false
    default: []
    help: "期望存在的文件模式列表"
  
  min_file_size:
    type: int
    required: false
    default: 0
    help: "最小文件大小（字节）"
  
  check_permissions:
    type: bool
    required: false
    default: false
    help: "是否检查文件权限"

command_template: 'python -m {{ python_module }} --path "{{ check_path }}" {% for pattern in expected_files %}--expect "{{ pattern }}" {% endfor %}{% if min_file_size > 0 %}--min-size {{ min_file_size }}{% endif %}{% if check_permissions %}--check-permissions{% endif %}'

success_pattern: "Validation passed"
failure_pattern: "Validation failed"
```

## 步骤2: 场景定义

```yaml
# scenarios/onnx_to_atc.scenario.yml
name: onnx-to-atc-conversion
description: "完整的ONNX模型生成和ATC转换流程"
version: "2.0"

default_params:
  output_dir: "outputs"
  log_level: "info"
  soc_version: "Ascend310"
  max_retries: 3

environment:
  ASCEND_OPP_PATH: "/usr/local/Ascend/opp"
  PYTHONPATH: "/usr/local/Ascend/pyACL/python/site-packages/acl"

steps:
  - name: generate_onnx
    tool: ai-json-operator
    description: "生成ONNX模型文件"
    params:
      ops: "{{ ops }}"
      convert_to_onnx: true
      max_retries: "{{ max_retries }}"
      output_dir: "{{ output_dir }}"
    retry_on_failure: true
    retry_count: 2
    timeout: 300

  - name: validate_onnx
    tool: file-validator
    description: "验证生成的ONNX文件"
    depends_on: ["generate_onnx"]
    params:
      check_path: "{{ steps.generate_onnx.outputs.onnx_file }}"
      min_file_size: 1000
      check_permissions: true
    continue_on_failure: false

  - name: convert_atc
    tool: atc
    description: "将ONNX模型转换为ATC格式"
    depends_on: ["validate_onnx"]
    params:
      framework: 5
      model: "{{ steps.generate_onnx.outputs.onnx_file }}"
      input_format: "NCHW"
      output: "{{ output_dir }}/atc_outputs/{{ model_name | default('model') }}"
      log: "{{ log_level }}"
      soc_version: "{{ soc_version }}"
    timeout: 600
    retry_on_failure: true
    retry_count: 1

  - name: validate_atc_output
    tool: file-validator
    description: "验证ATC转换输出"
    depends_on: ["convert_atc"]
    params:
      check_path: "{{ output_dir }}/atc_outputs"
      expected_files: ["*.om"]
      min_file_size: 1000
      check_permissions: true

cleanup_steps:
  - name: cleanup_temp_files
    tool: file-cleaner
    params:
      directories: ["{{ output_dir }}/temp"]
      patterns: ["*.tmp", "*.cache"]
      preserve_logs: true

validation:
  type: "complete_pipeline"
  rules:
    - all_critical_steps_success: ["generate_onnx", "convert_atc", "validate_atc_output"]
    - execution_time_limit: 1800
    - output_files_exist: ["{{ output_dir }}/atc_outputs/*.om"]
```

## 步骤3: 测试用例定义

### 基础端到端测试

```yaml
# cases/e2e_onnx_to_atc.case.yml
common_params:
  output_base_dir: "test_outputs"
  log_level: "info"
  soc_version: "Ascend310"

tags: ["e2e", "integration"]

cases:
  - name: test_conv_add_e2e
    description: "Conv Add算子端到端转换测试"
    tags: ["smoke", "conv", "add"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv Add"
      output_dir: "{{ output_base_dir }}/conv_add"
      model_name: "conv_add_model"
    
    setup:
      create_dirs: ["{{ output_base_dir }}/conv_add"]
    
    validation:
      - type: exit_code
        expected: 0
        description: "场景应该成功执行"
      
      - type: file_exists
        target: "{{ output_base_dir }}/conv_add/atc_outputs/*.om"
        description: "应该生成ATC模型文件"
      
      - type: file_size
        target: "{{ output_base_dir }}/conv_add/atc_outputs/*.om"
        min_value: 1000
        description: "ATC文件应该有合理大小"
    
    teardown:
      preserve_files: ["*.log", "*.om"]
      cleanup_dirs: ["{{ output_base_dir }}/conv_add/temp"]

  - name: test_complex_operators_e2e
    description: "复杂算子组合端到端转换测试"
    tags: ["regression", "complex"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv BatchNorm ReLU MaxPool"
      output_dir: "{{ output_base_dir }}/complex_ops"
      model_name: "complex_model"
      soc_version: "Ascend310P3"
    
    validation:
      - type: exit_code
        expected: 0
      
      - type: file_exists
        target: "{{ output_base_dir }}/complex_ops/atc_outputs/*.om"
      
      - type: custom
        function: "validate_model_structure"
        params:
          model_file: "{{ output_base_dir }}/complex_ops/atc_outputs/*.om"
          expected_layers: 4
    
    timeout: 900

  - name: test_error_handling
    description: "测试无效算子的错误处理"
    tags: ["negative", "error_handling"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "InvalidOperator"
      output_dir: "{{ output_base_dir }}/invalid_op"
    
    validation:
      - type: exit_code
        expected: 1  # 期望失败
        description: "无效算子应该导致失败"
      
      - type: stderr_contains
        patterns: ["Invalid operator", "not supported"]
        description: "错误信息应该包含相关提示"
    
    teardown:
      cleanup_dirs: ["{{ output_base_dir }}/invalid_op"]

# 数据驱动的批量测试
data_driven_cases:
  - template:
      name: "test_soc_compatibility_{{ item.soc_version }}"
      description: "测试{{ item.soc_version }}的兼容性"
      tags: ["compatibility", "{{ item.soc_version.lower() }}"]
      scenario: onnx-to-atc-conversion
      params:
        ops: "Conv Add"
        soc_version: "{{ item.soc_version }}"
        output_dir: "{{ output_base_dir }}/compat_{{ item.soc_version }}"
        model_name: "compat_test_{{ item.soc_version }}"
      
      validation:
        - type: exit_code
          expected: 0
        - type: file_exists
          target: "{{ output_base_dir }}/compat_{{ item.soc_version }}/atc_outputs/*.om"
    
    data:
      - soc_version: "Ascend310"
      - soc_version: "Ascend310P3"
      - soc_version: "Ascend910"
```

## 步骤4: 执行测试

### 运行基础测试

```bash
# 切换到示例目录
cd examples

# 运行所有端到端测试
dact cases/e2e_onnx_to_atc.case.yml

# 运行特定测试用例
dact cases/e2e_onnx_to_atc.case.yml -k "test_conv_add_e2e"

# 运行带详细输出的测试
dact cases/e2e_onnx_to_atc.case.yml -v

# 生成HTML报告
dact cases/e2e_onnx_to_atc.case.yml --html=report.html
```

### 运行数据驱动测试

```bash
# 运行兼容性测试
dact cases/e2e_onnx_to_atc.case.yml -k "soc_compatibility"

# 运行特定SoC版本的测试
dact cases/e2e_onnx_to_atc.case.yml -k "ascend310"
```

### 调试失败的测试

```bash
# 使用调试模式
dact cases/e2e_onnx_to_atc.case.yml --debug -v

# 从上次失败处继续
dact cases/e2e_onnx_to_atc.case.yml --resume

# 查看详细日志
ls -la tmp/test_conv_add_e2e/
cat tmp/test_conv_add_e2e/generate_onnx/stdout.log
```

## 步骤5: 结果分析

### 测试输出结构

```
tmp/
├── test_conv_add_e2e/              # 测试用例工作目录
│   ├── generate_onnx/              # 第一步：生成ONNX
│   │   ├── stdout.log              # 标准输出日志
│   │   ├── stderr.log              # 标准错误日志
│   │   └── command.txt             # 执行的命令
│   ├── validate_onnx/              # 第二步：验证ONNX
│   │   ├── stdout.log
│   │   ├── stderr.log
│   │   └── command.txt
│   ├── convert_atc/                # 第三步：ATC转换
│   │   ├── stdout.log
│   │   ├── stderr.log
│   │   └── command.txt
│   └── validate_atc_output/        # 第四步：验证输出
│       ├── stdout.log
│       ├── stderr.log
│       └── command.txt
└── test_outputs/                   # 实际输出文件
    └── conv_add/
        ├── Conv_testcase_98bd3f/   # 动态生成的目录
        │   └── resources/
        │       └── Conv_testcase_98bd3f.onnx
        └── atc_outputs/
            ├── conv_add_model.om   # ATC转换结果
            └── conv_add_model.log  # 转换日志
```

### 验证结果

成功的测试应该产生：

1. **ONNX文件生成**
   - 在 `test_outputs/conv_add/` 下生成ONNX文件
   - 文件大小 > 1000 字节
   - 文件结构正确

2. **ATC转换成功**
   - 在 `test_outputs/conv_add/atc_outputs/` 下生成 `.om` 文件
   - 转换日志包含 "ATC run success"
   - 退出码为 0

3. **验证通过**
   - 所有验证规则通过
   - 文件权限正确
   - 无错误信息

## 步骤6: 扩展和定制

### 添加新的算子测试

```yaml
# 在测试用例中添加新的算子组合
cases:
  - name: test_transformer_blocks
    description: "Transformer块算子测试"
    tags: ["transformer", "attention"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "MatMul Add LayerNorm Softmax"
      output_dir: "{{ output_base_dir }}/transformer"
      model_name: "transformer_block"
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "{{ output_base_dir }}/transformer/atc_outputs/*.om"
```

### 添加性能测试

```yaml
cases:
  - name: test_performance_benchmark
    description: "性能基准测试"
    tags: ["performance", "benchmark"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv BatchNorm ReLU"
      output_dir: "{{ output_base_dir }}/performance"
      run_performance_test: true
      performance_iterations: 1000
    
    validation:
      - type: exit_code
        expected: 0
      - type: performance
        metrics:
          execution_time:
            max_value: 120  # 2分钟内完成
          memory_usage:
            max_value: 4096  # 最大4GB内存
    
    timeout: 1800
```

### 添加自定义验证

```python
# 创建自定义验证函数
def validate_model_structure(model_file, expected_layers):
    """验证模型结构"""
    # 实现模型结构验证逻辑
    pass

def validate_model_accuracy(model_file, test_data, threshold):
    """验证模型精度"""
    # 实现精度验证逻辑
    pass
```

## 最佳实践

### 1. 测试设计原则

- **独立性**: 每个测试用例应该独立运行
- **可重复性**: 测试结果应该是确定性的
- **快速反馈**: 优先运行快速的冒烟测试
- **全面覆盖**: 包含正常和异常情况的测试

### 2. 参数管理

- **使用公共参数**: 减少重复配置
- **环境适配**: 根据环境动态调整参数
- **参数验证**: 在工具中验证参数有效性

### 3. 错误处理

- **分级处理**: 区分致命错误和警告
- **重试机制**: 为不稳定的操作设置重试
- **清理资源**: 确保测试后的资源清理

### 4. 日志和调试

- **结构化日志**: 使用一致的日志格式
- **保留关键信息**: 保存足够的调试信息
- **分级输出**: 支持不同详细程度的输出

## 故障排除

### 常见问题和解决方案

1. **工具未找到**
   ```bash
   # 检查工具是否在PATH中
   which ai-json-operator
   which atc
   
   # 检查工具配置
   dact list-tools
   ```

2. **ONNX文件未找到**
   ```bash
   # 检查输出目录
   ls -la test_outputs/conv_add/
   
   # 查看生成日志
   cat tmp/test_conv_add_e2e/generate_onnx/stdout.log
   ```

3. **ATC转换失败**
   ```bash
   # 查看ATC日志
   cat tmp/test_conv_add_e2e/convert_atc/stderr.log
   
   # 检查模型文件
   file test_outputs/conv_add/*/resources/*.onnx
   ```

4. **参数传递错误**
   ```bash
   # 查看渲染后的命令
   cat tmp/test_conv_add_e2e/*/command.txt
   
   # 使用调试模式
   dact cases/e2e_onnx_to_atc.case.yml --debug -v
   ```

## 总结

这个完整的端到端测试示例展示了：

1. **工具定义**: 如何定义和配置测试工具
2. **场景编排**: 如何组织多步骤的测试流程
3. **测试用例**: 如何编写全面的测试用例
4. **参数传递**: 如何在步骤间传递参数
5. **验证规则**: 如何设置多层次的验证
6. **错误处理**: 如何处理异常情况
7. **数据驱动**: 如何进行批量测试

通过这个示例，您可以：
- 快速上手DACT Pipeline的端到端测试功能
- 理解工具、场景、用例三层架构的设计理念
- 学习如何扩展和定制测试流程
- 掌握调试和故障排除的技巧

更多详细信息请参考：
- [工具定义指南](../docs/guides/tool_definition_guide.md)
- [场景定义指南](../docs/guides/scenario_definition_guide.md)
- [测试用例编写指南](../docs/guides/case_writing_guide.md)