# 测试用例编写指南

本指南详细介绍如何在 DACT Pipeline 中编写和管理测试用例。

## 概述

测试用例 (Case) 是 DACT Pipeline 的执行单元，为场景或工具提供具体的输入参数和验证规则。测试用例实现了测试逻辑与测试数据的分离，支持数据驱动测试和参数化测试。

## 测试用例文件结构

测试用例文件使用 `.case.yml` 扩展名，可以放置在任意目录下（通常是 `cases/` 目录）。

### 基本结构

```yaml
# 文件级别配置
common_params:                      # 公共参数（可选）
  param_name: value
tags: ["tag1", "tag2"]             # 文件标签（可选）
timeout: 300                       # 默认超时（可选）

# 测试用例列表
cases:
  - name: test_case_1              # 用例名称（必需）
    description: "测试用例描述"     # 用例描述（可选）
    tags: ["smoke", "regression"]   # 用例标签（可选）
    scenario: scenario-name         # 关联场景（scenario或tool二选一）
    tool: tool-name                 # 直接调用工具（scenario或tool二选一）
    params:                         # 用例参数（可选）
      param1: value1
    validation:                     # 验证规则（可选）
      - type: exit_code
        expected: 0
    setup:                          # 前置条件（可选）
      files: ["input.txt"]
    teardown:                       # 后置清理（可选）
      cleanup_dirs: ["temp"]
    timeout: 600                    # 用例超时（可选）
    retry_count: 0                  # 重试次数（可选）

# 数据驱动测试用例（可选）
data_driven_cases:
  - template:                       # 用例模板
      name: "batch_test_{{ item.name }}"
      scenario: test-scenario
      params:
        input: "{{ item.input }}"
        expected: "{{ item.expected }}"
    data:                           # 测试数据
      - name: "case1"
        input: "data1.txt"
        expected: "result1.txt"
      - name: "case2"
        input: "data2.txt"
        expected: "result2.txt"
```

## 基本测试用例

### 场景关联用例

```yaml
cases:
  - name: test_conv_add_e2e
    description: "Conv Add算子端到端转换测试"
    tags: ["e2e", "conv", "add"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv Add"
      soc_version: "Ascend310"
      output_dir: "outputs/conv_add"
    validation:
      - type: exit_code
        expected: 0
        description: "场景应该成功执行"
      - type: file_exists
        target: "outputs/conv_add/atc_outputs/*.om"
        description: "应该生成ATC模型文件"
```

### 直接工具调用用例

```yaml
cases:
  - name: test_onnx_generation
    description: "直接测试ONNX生成工具"
    tags: ["unit", "onnx"]
    tool: ai-json-operator
    params:
      ops: "Conv BatchNorm ReLU"
      convert_to_onnx: true
      max_retries: 3
      output_dir: "outputs/direct_test"
    validation:
      - type: exit_code
        expected: 0
      - type: stdout_contains
        patterns: ["Generation completed successfully"]
      - type: file_exists
        target: "outputs/direct_test/**/*.onnx"
```

## 参数管理

### 公共参数

文件级别的公共参数会应用到所有测试用例：

```yaml
common_params:
  output_base_dir: "test_outputs"
  log_level: "debug"
  timeout: 300
  soc_version: "Ascend310"

cases:
  - name: test_case_1
    scenario: scenario1
    params:
      # 自动继承公共参数
      specific_param: "value1"
  
  - name: test_case_2
    scenario: scenario2
    params:
      # 可以覆盖公共参数
      log_level: "info"
      specific_param: "value2"
```

### 参数覆盖

测试用例可以覆盖场景中的默认参数：

```yaml
cases:
  - name: test_custom_config
    scenario: standard-pipeline
    params:
      # 覆盖场景中的步骤参数
      generate_onnx:
        ops: "Custom Op"
        output_dir: "custom_outputs"
      convert_atc:
        soc_version: "Ascend310P3"
        precision_mode: "allow_mix_precision"
```

### 动态参数

支持使用表达式和函数生成动态参数：

```yaml
cases:
  - name: test_with_timestamp
    scenario: data-processing
    params:
      output_dir: "outputs/{{ timestamp() }}"
      batch_id: "{{ uuid4() }}"
      config_file: "configs/{{ env.USER }}_config.json"
      data_size: "{{ random_int(100, 1000) }}"
```

## 验证规则

### 基本验证类型

```yaml
validation:
  # 退出码验证
  - type: exit_code
    expected: 0
    description: "工具应该成功执行"
  
  # 标准输出验证
  - type: stdout_contains
    patterns: ["success", "completed"]
    description: "输出应包含成功信息"
  
  - type: stdout_not_contains
    patterns: ["error", "failed"]
    description: "输出不应包含错误信息"
  
  # 标准错误验证
  - type: stderr_empty
    description: "标准错误应为空"
  
  - type: stderr_contains
    patterns: ["warning"]
    description: "可以包含警告信息"
  
  # 文件验证
  - type: file_exists
    target: "outputs/**/*.onnx"
    description: "应该生成ONNX文件"
  
  - type: file_not_exists
    target: "outputs/**/*.tmp"
    description: "不应有临时文件残留"
  
  - type: file_size
    target: "outputs/model.om"
    min_value: 1000
    max_value: 10000000
    description: "模型文件大小应在合理范围内"
  
  # 目录验证
  - type: directory_exists
    target: "outputs/logs"
    description: "日志目录应该存在"
  
  - type: directory_not_empty
    target: "outputs/results"
    description: "结果目录不应为空"
```

### 高级验证

```yaml
validation:
  # JSON内容验证
  - type: json_content
    target: "outputs/metadata.json"
    schema:
      type: object
      properties:
        model_name:
          type: string
        accuracy:
          type: number
          minimum: 0.8
    description: "元数据应符合预期格式"
  
  # 自定义验证函数
  - type: custom
    function: "validate_model_accuracy"
    params:
      model_file: "outputs/model.om"
      test_data: "test_data.bin"
      threshold: 0.95
    description: "模型精度应达到要求"
  
  # 性能验证
  - type: performance
    metrics:
      execution_time:
        max_value: 300  # 最大执行时间（秒）
      memory_usage:
        max_value: 2048  # 最大内存使用（MB）
      cpu_usage:
        max_value: 80   # 最大CPU使用率（%）
    description: "性能指标应在预期范围内"
```

## 前置和后置处理

### 前置条件 (Setup)

```yaml
cases:
  - name: test_with_setup
    scenario: data-processing
    setup:
      # 创建必需的目录
      create_dirs: ["inputs", "outputs", "temp"]
      
      # 复制测试文件
      copy_files:
        - src: "test_data/sample.txt"
          dst: "inputs/sample.txt"
        - src: "configs/default.json"
          dst: "inputs/config.json"
      
      # 设置环境变量
      environment:
        TEST_MODE: "true"
        DATA_PATH: "inputs"
      
      # 执行前置命令
      commands:
        - "chmod +x scripts/prepare.sh"
        - "./scripts/prepare.sh"
      
      # 检查前置条件
      checks:
        - type: file_exists
          target: "inputs/sample.txt"
        - type: command_available
          command: "python3"
    
    params:
      input_file: "inputs/sample.txt"
      config_file: "inputs/config.json"
```

### 后置清理 (Teardown)

```yaml
cases:
  - name: test_with_cleanup
    scenario: model-training
    teardown:
      # 清理目录
      cleanup_dirs: ["temp", "cache"]
      
      # 删除文件
      cleanup_files: ["*.tmp", "*.cache"]
      
      # 保留重要文件
      preserve_files: ["*.log", "outputs/*.model"]
      
      # 执行清理命令
      commands:
        - "./scripts/cleanup.sh"
        - "docker stop test-container"
      
      # 重置环境变量
      reset_environment: ["TEST_MODE", "TEMP_DIR"]
      
      # 条件清理
      conditional_cleanup:
        - condition: "{{ test_failed }}"
          actions:
            - "cp -r outputs debug_outputs"
            - "tar -czf debug_{{ timestamp }}.tar.gz debug_outputs"
```

## 数据驱动测试

### 基本数据驱动

```yaml
data_driven_cases:
  - template:
      name: "test_operator_{{ item.op_name }}"
      description: "测试{{ item.op_name }}算子转换"
      scenario: onnx-to-atc-conversion
      params:
        ops: "{{ item.ops }}"
        soc_version: "{{ item.soc_version }}"
      validation:
        - type: exit_code
          expected: 0
        - type: file_exists
          target: "outputs/**/*.om"
    
    data:
      - op_name: "conv_add"
        ops: "Conv Add"
        soc_version: "Ascend310"
      - op_name: "conv_bn_relu"
        ops: "Conv BatchNorm ReLU"
        soc_version: "Ascend310P3"
      - op_name: "lstm"
        ops: "LSTM"
        soc_version: "Ascend910"
```

### 外部数据源

```yaml
data_driven_cases:
  - template:
      name: "test_model_{{ item.model_name }}"
      scenario: model-conversion
      params:
        model_path: "{{ item.model_path }}"
        target_format: "{{ item.target_format }}"
        optimization_level: "{{ item.optimization_level }}"
    
    # 从CSV文件加载数据
    data_source:
      type: "csv"
      file: "test_data/model_test_cases.csv"
      columns:
        - "model_name"
        - "model_path"
        - "target_format"
        - "optimization_level"
```

```csv
# test_data/model_test_cases.csv
model_name,model_path,target_format,optimization_level
resnet50,models/resnet50.onnx,tensorrt,2
mobilenet,models/mobilenet.onnx,tflite,1
bert_base,models/bert_base.onnx,openvino,3
```

### 参数化测试

```yaml
cases:
  - name: test_multiple_soc_versions
    description: "测试多个SoC版本的兼容性"
    scenario: atc-conversion
    parameterized:
      parameters:
        soc_version: ["Ascend310", "Ascend310P3", "Ascend910"]
        precision_mode: ["allow_fp32_to_fp16", "allow_mix_precision"]
      combinations: "all"  # 生成所有组合
    params:
      model_file: "models/test_model.onnx"
      output_dir: "outputs/{{ soc_version }}_{{ precision_mode }}"
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "outputs/{{ soc_version }}_{{ precision_mode }}/*.om"
```

## 标签和过滤

### 标签定义

```yaml
# 文件级别标签
tags: ["integration", "slow"]

cases:
  - name: test_smoke
    tags: ["smoke", "quick"]
    # ...
  
  - name: test_regression
    tags: ["regression", "comprehensive"]
    # ...
  
  - name: test_performance
    tags: ["performance", "slow", "gpu"]
    # ...
```

### 标签使用

```bash
# 运行特定标签的测试
dact cases/ -k "smoke"
dact cases/ -k "regression and not slow"
dact cases/ -k "performance or gpu"

# 使用pytest标记
dact cases/ -m "smoke"
dact cases/ -m "not slow"
```

## 错误处理和重试

### 重试配置

```yaml
cases:
  - name: test_unstable_service
    scenario: service-test
    retry_count: 3
    retry_delay: 10
    retry_on_exit_codes: [1, 2, 130]  # 仅在特定退出码时重试
    params:
      service_url: "http://unstable-service:8080"
    validation:
      - type: exit_code
        expected: 0
```

### 条件执行

```yaml
cases:
  - name: test_gpu_dependent
    scenario: gpu-training
    condition: "{{ gpu_available() }}"  # 仅在GPU可用时执行
    params:
      device: "cuda:0"
  
  - name: test_large_dataset
    scenario: data-processing
    condition: "{{ disk_space_gb() > 10 }}"  # 仅在磁盘空间足够时执行
    params:
      dataset_size: "large"
```

## 完整示例

### 综合测试用例文件

```yaml
# comprehensive_test.case.yml
common_params:
  base_output_dir: "test_outputs"
  log_level: "info"
  timeout: 600

tags: ["comprehensive", "e2e"]

cases:
  # 基本功能测试
  - name: test_basic_conv_add
    description: "基本Conv Add算子转换测试"
    tags: ["smoke", "basic"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv Add"
      soc_version: "Ascend310"
      output_dir: "{{ base_output_dir }}/basic_conv_add"
    setup:
      create_dirs: ["{{ base_output_dir }}/basic_conv_add"]
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "{{ base_output_dir }}/basic_conv_add/atc_outputs/*.om"
      - type: file_size
        target: "{{ base_output_dir }}/basic_conv_add/atc_outputs/*.om"
        min_value: 1000
    teardown:
      preserve_files: ["*.log", "*.om"]
  
  # 复杂算子测试
  - name: test_complex_operators
    description: "复杂算子组合转换测试"
    tags: ["regression", "complex"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "Conv BatchNorm ReLU MaxPool Flatten Dense"
      soc_version: "Ascend310P3"
      output_dir: "{{ base_output_dir }}/complex_ops"
      precision_mode: "allow_mix_precision"
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "{{ base_output_dir }}/complex_ops/atc_outputs/*.om"
      - type: custom
        function: "validate_model_structure"
        params:
          model_file: "{{ base_output_dir }}/complex_ops/atc_outputs/*.om"
          expected_layers: 6
    timeout: 900
  
  # 错误处理测试
  - name: test_invalid_operator
    description: "测试无效算子的错误处理"
    tags: ["negative", "error_handling"]
    scenario: onnx-to-atc-conversion
    params:
      ops: "InvalidOperator"
      soc_version: "Ascend310"
      output_dir: "{{ base_output_dir }}/invalid_op"
    validation:
      - type: exit_code
        expected: 1  # 期望失败
      - type: stderr_contains
        patterns: ["Invalid operator", "not supported"]
    teardown:
      cleanup_dirs: ["{{ base_output_dir }}/invalid_op"]
  
  # 性能测试
  - name: test_performance_benchmark
    description: "性能基准测试"
    tags: ["performance", "slow"]
    scenario: onnx-to-atc-conversion
    condition: "{{ run_performance_tests | default(false) }}"
    params:
      ops: "Conv BatchNorm ReLU"
      soc_version: "Ascend910"
      output_dir: "{{ base_output_dir }}/performance"
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
        output_dir: "{{ base_output_dir }}/compat_{{ item.soc_version }}"
        precision_mode: "{{ item.precision_mode }}"
      validation:
        - type: exit_code
          expected: 0
        - type: file_exists
          target: "{{ base_output_dir }}/compat_{{ item.soc_version }}/atc_outputs/*.om"
    
    data:
      - soc_version: "Ascend310"
        precision_mode: "allow_fp32_to_fp16"
      - soc_version: "Ascend310P3"
        precision_mode: "allow_mix_precision"
      - soc_version: "Ascend910"
        precision_mode: "allow_fp32_to_fp16"

# 参数化测试
  - template:
      name: "test_precision_modes_{{ item.precision_mode }}"
      description: "测试精度模式: {{ item.precision_mode }}"
      tags: ["precision", "parameterized"]
      scenario: onnx-to-atc-conversion
      params:
        ops: "Conv BatchNorm ReLU"
        soc_version: "Ascend310"
        precision_mode: "{{ item.precision_mode }}"
        output_dir: "{{ base_output_dir }}/precision_{{ item.precision_mode }}"
      validation:
        - type: exit_code
          expected: 0
        - type: custom
          function: "validate_precision_mode"
          params:
            model_file: "{{ base_output_dir }}/precision_{{ item.precision_mode }}/atc_outputs/*.om"
            expected_precision: "{{ item.precision_mode }}"
    
    data:
      - precision_mode: "allow_fp32_to_fp16"
      - precision_mode: "allow_mix_precision"
      - precision_mode: "must_keep_origin_dtype"
```

## 最佳实践

### 1. 用例设计

- **单一职责**: 每个测试用例专注于测试一个特定功能
- **独立性**: 测试用例之间不应相互依赖
- **可重复**: 测试结果应该是确定性和可重复的
- **快速反馈**: 优先编写快速执行的测试用例

### 2. 命名规范

- **描述性**: 用例名称应清楚描述测试内容
- **一致性**: 使用统一的命名模式
- **分类**: 通过前缀或标签进行分类

```yaml
# 好的命名示例
cases:
  - name: test_conv_add_basic_functionality
  - name: test_atc_conversion_with_optimization
  - name: test_error_handling_invalid_input
  - name: test_performance_large_model
```

### 3. 参数管理

- **默认值**: 为常用参数设置合理默认值
- **参数化**: 使用参数化测试覆盖多种场景
- **环境适配**: 根据环境动态调整参数

### 4. 验证策略

- **多层验证**: 结合退出码、输出内容、文件检查等
- **业务验证**: 添加业务逻辑相关的验证规则
- **性能验证**: 包含必要的性能指标检查

### 5. 错误处理

- **预期失败**: 明确标识预期失败的测试用例
- **错误分类**: 区分不同类型的错误和处理方式
- **调试信息**: 保留足够的调试信息

## 调试和故障排除

### 常见问题

1. **参数传递错误**
   - 检查参数名称拼写
   - 验证参数类型匹配
   - 查看参数渲染结果

2. **验证规则失败**
   - 检查期望值设置
   - 验证文件路径和模式
   - 查看详细的验证日志

3. **前置条件失败**
   - 检查文件和目录权限
   - 验证依赖工具可用性
   - 查看前置命令执行结果

### 调试技巧

1. **使用调试模式**
   ```bash
   dact cases/test.case.yml --debug -v
   ```

2. **查看执行日志**
   ```bash
   # 检查详细的执行日志
   ls -la tmp/test_case_name/
   cat tmp/test_case_name/*/stdout.log
   ```

3. **单步调试**
   - 创建简化版本的测试用例
   - 逐步添加验证规则
   - 使用直接工具调用测试

4. **参数验证**
   ```bash
   # 使用list-cases检查用例配置
   dact list-cases --file cases/test.case.yml
   ```

## 参考资料

- [工具定义指南](tool_definition_guide.md)
- [场景定义指南](scenario_definition_guide.md)
- [端到端测试指南](../e2e_testing_guide.md)
- [API参考文档](../api_reference.md)