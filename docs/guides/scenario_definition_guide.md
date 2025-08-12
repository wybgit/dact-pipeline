# 场景定义指南

本指南详细介绍如何在 DACT Pipeline 中定义和管理测试场景。

## 概述

场景 (Scenario) 是 DACT Pipeline 的核心组件，用于编排多个工具的执行顺序和依赖关系。场景定义了一个完整的测试工作流，包括步骤执行、参数传递、依赖管理等。

## 场景配置文件结构

场景配置文件使用 `.scenario.yml` 扩展名，应放置在 `scenarios/` 目录下。

### 基本结构

```yaml
name: scenario-name                  # 场景名称（必需）
description: "场景描述"              # 场景描述（可选）
version: "1.0"                      # 版本号（可选）
default_params:                     # 默认参数（可选）
  param_name: value
environment:                        # 环境变量（可选）
  ENV_VAR: value
steps:                              # 执行步骤（必需）
  - name: step1                     # 步骤名称
    tool: tool-name                 # 使用的工具
    description: "步骤描述"         # 步骤描述（可选）
    params:                         # 步骤参数
      param1: value1
    depends_on: ["step0"]           # 依赖的步骤（可选）
    condition: "{{ condition }}"    # 执行条件（可选）
    retry_on_failure: false         # 失败重试（可选）
    continue_on_failure: false      # 失败继续（可选）
    timeout: 300                    # 步骤超时（可选）
cleanup_steps:                     # 清理步骤（可选）
  - name: cleanup
    tool: cleanup-tool
validation:                         # 场景验证（可选）
  type: "complete_pipeline"
  rules: []
```

## 步骤定义

### 基本步骤

```yaml
steps:
  - name: generate_model
    tool: ai-json-operator
    description: "生成ONNX模型文件"
    params:
      ops: "{{ ops }}"
      convert_to_onnx: true
      output_dir: "outputs"
```

### 依赖步骤

```yaml
steps:
  - name: generate_model
    tool: ai-json-operator
    params:
      ops: "Conv Add"
      convert_to_onnx: true
      output_dir: "outputs"
  
  - name: convert_model
    tool: atc
    description: "转换模型为ATC格式"
    depends_on: ["generate_model"]  # 依赖前一个步骤
    params:
      framework: 5
      model: "{{ steps.generate_model.outputs.onnx_file }}"  # 使用前一步的输出
      output: "outputs/atc_outputs"
```

### 条件执行

```yaml
steps:
  - name: optimize_model
    tool: optimizer
    condition: "{{ optimization_enabled }}"  # 仅在优化启用时执行
    params:
      model: "{{ model_path }}"
      level: "{{ optimization_level }}"
  
  - name: validate_accuracy
    tool: validator
    condition: "{{ steps.optimize_model.status == 'success' }}"  # 仅在优化成功时执行
    params:
      model: "{{ steps.optimize_model.outputs.optimized_model }}"
```

## 参数传递

### 默认参数

场景级别的默认参数会传递给所有步骤：

```yaml
name: model-pipeline
default_params:
  output_dir: "outputs"
  log_level: "info"
  soc_version: "Ascend310"

steps:
  - name: step1
    tool: tool1
    params:
      # 自动继承 output_dir, log_level, soc_version
      specific_param: "value"
  
  - name: step2
    tool: tool2
    params:
      # 可以覆盖默认参数
      output_dir: "custom_outputs"
      another_param: "value"
```

### 步骤间参数传递

使用 Jinja2 模板语法引用前置步骤的输出：

```yaml
steps:
  - name: generate_data
    tool: data-generator
    params:
      count: 1000
      format: "json"
  
  - name: process_data
    tool: data-processor
    depends_on: ["generate_data"]
    params:
      input_file: "{{ steps.generate_data.outputs.data_file }}"
      output_file: "processed_data.json"
  
  - name: analyze_results
    tool: analyzer
    depends_on: ["process_data"]
    params:
      data_file: "{{ steps.process_data.outputs.output_file }}"
      metrics: ["accuracy", "performance"]
      threshold: "{{ steps.generate_data.outputs.quality_threshold }}"
```

### 复杂参数传递

```yaml
steps:
  - name: multi_output_step
    tool: complex-tool
    params:
      input: "data.txt"
  
  - name: use_multiple_outputs
    tool: consumer-tool
    depends_on: ["multi_output_step"]
    params:
      # 使用多个输出
      model_file: "{{ steps.multi_output_step.outputs.model }}"
      config_file: "{{ steps.multi_output_step.outputs.config }}"
      log_file: "{{ steps.multi_output_step.outputs.log }}"
      
      # 使用计算表达式
      batch_size: "{{ steps.multi_output_step.outputs.data_size // 10 }}"
      
      # 使用条件表达式
      mode: "{{ 'production' if steps.multi_output_step.outputs.accuracy > 0.95 else 'debug' }}"
```

## 依赖管理

### 显式依赖

```yaml
steps:
  - name: step_a
    tool: tool_a
  
  - name: step_b
    tool: tool_b
  
  - name: step_c
    tool: tool_c
    depends_on: ["step_a", "step_b"]  # 等待 step_a 和 step_b 完成
```

### 隐式依赖

系统会自动检测参数引用创建的隐式依赖：

```yaml
steps:
  - name: step_a
    tool: tool_a
  
  - name: step_b
    tool: tool_b
    params:
      input: "{{ steps.step_a.outputs.result }}"  # 自动创建对 step_a 的依赖
```

### 依赖验证

系统会在执行前验证依赖关系：

- 检测循环依赖
- 验证引用的步骤是否存在
- 确保依赖图的完整性

## 错误处理

### 失败重试

```yaml
steps:
  - name: unstable_step
    tool: unstable-tool
    retry_on_failure: true
    retry_count: 3
    retry_delay: 10
    params:
      input: "data.txt"
```

### 失败继续

```yaml
steps:
  - name: optional_step
    tool: optional-tool
    continue_on_failure: true  # 即使失败也继续执行后续步骤
    params:
      input: "data.txt"
  
  - name: required_step
    tool: required-tool
    depends_on: ["optional_step"]
    params:
      # 可以检查前一步的状态
      input: "{{ steps.optional_step.outputs.result if steps.optional_step.status == 'success' else 'default.txt' }}"
```

### 清理步骤

```yaml
cleanup_steps:
  - name: cleanup_temp_files
    tool: file-cleaner
    params:
      directory: "{{ temp_dir }}"
      pattern: "*.tmp"
  
  - name: stop_services
    tool: service-manager
    params:
      action: "stop"
      services: ["test-service"]
```

## 环境变量

```yaml
name: environment-aware-scenario
environment:
  CUDA_VISIBLE_DEVICES: "0,1"
  OMP_NUM_THREADS: "4"
  MODEL_CACHE_DIR: "/tmp/model_cache"
  LOG_LEVEL: "{{ log_level | default('INFO') }}"

steps:
  - name: gpu_task
    tool: gpu-tool
    params:
      device_count: "{{ env.CUDA_VISIBLE_DEVICES.split(',') | length }}"
```

## 场景验证

### 基本验证

```yaml
validation:
  type: "complete_pipeline"
  rules:
    - all_steps_success: true
    - execution_time_limit: 3600  # 1小时
    - output_files_exist: ["final_output.txt"]
```

### 自定义验证

```yaml
validation:
  type: "custom"
  validators:
    - name: "check_model_accuracy"
      function: "validate_model_accuracy"
      params:
        threshold: 0.95
        test_data: "validation_set.json"
    
    - name: "check_performance"
      function: "validate_performance"
      params:
        max_latency: 100  # ms
        min_throughput: 1000  # ops/sec
```

## 完整示例

### ONNX到ATC转换场景

```yaml
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
  - name: prepare_environment
    tool: env-setup
    description: "准备执行环境"
    params:
      check_dependencies: true
      setup_paths: true
    timeout: 60
  
  - name: generate_onnx
    tool: ai-json-operator
    description: "生成ONNX模型文件"
    depends_on: ["prepare_environment"]
    params:
      ops: "{{ ops }}"
      convert_to_onnx: true
      max_retries: "{{ max_retries }}"
      output_dir: "{{ output_dir }}"
      log_level: "{{ log_level }}"
    retry_on_failure: true
    retry_count: 2
    timeout: 300
  
  - name: validate_onnx
    tool: onnx-validator
    description: "验证生成的ONNX模型"
    depends_on: ["generate_onnx"]
    params:
      model_file: "{{ steps.generate_onnx.outputs.onnx_file }}"
      check_structure: true
      check_weights: true
    continue_on_failure: false
  
  - name: convert_atc
    tool: atc
    description: "将ONNX模型转换为ATC格式"
    depends_on: ["validate_onnx"]
    condition: "{{ steps.validate_onnx.status == 'success' }}"
    params:
      framework: 5
      model: "{{ steps.generate_onnx.outputs.onnx_file }}"
      input_format: "NCHW"
      output: "{{ output_dir }}/atc_outputs/{{ model_name | default('model') }}"
      log: "{{ log_level }}"
      soc_version: "{{ soc_version }}"
      precision_mode: "{{ precision_mode | default('allow_fp32_to_fp16') }}"
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
  
  - name: performance_test
    tool: performance-tester
    description: "性能测试（可选）"
    depends_on: ["validate_atc_output"]
    condition: "{{ run_performance_test | default(false) }}"
    continue_on_failure: true
    params:
      model_file: "{{ steps.convert_atc.outputs.om_file }}"
      test_data: "{{ test_data_path | default('test_data.bin') }}"
      iterations: "{{ performance_iterations | default(100) }}"
    timeout: 1800

cleanup_steps:
  - name: cleanup_temp_files
    tool: file-cleaner
    params:
      directories: ["{{ output_dir }}/temp", "/tmp/onnx_*"]
      patterns: ["*.tmp", "*.cache"]
      preserve_logs: true
  
  - name: archive_results
    tool: archiver
    condition: "{{ archive_results | default(false) }}"
    params:
      source_dir: "{{ output_dir }}"
      archive_name: "{{ model_name }}_{{ timestamp }}.tar.gz"
      destination: "archives/"

validation:
  type: "complete_pipeline"
  rules:
    - all_critical_steps_success: ["generate_onnx", "convert_atc", "validate_atc_output"]
    - execution_time_limit: 1800
    - output_files_exist: ["{{ output_dir }}/atc_outputs/*.om"]
  
  custom_validators:
    - name: "validate_model_compatibility"
      function: "check_soc_compatibility"
      params:
        soc_version: "{{ soc_version }}"
        model_file: "{{ steps.convert_atc.outputs.om_file }}"
```

## 最佳实践

### 1. 场景设计

- **单一职责**: 每个场景应专注于一个特定的工作流
- **模块化**: 将复杂流程分解为多个简单场景
- **可重用**: 设计通用的场景模板，通过参数定制

### 2. 步骤组织

- **清晰命名**: 使用描述性的步骤名称
- **合理分组**: 将相关步骤组织在一起
- **适当粒度**: 避免步骤过于细碎或过于粗糙

### 3. 依赖管理

- **显式声明**: 明确声明关键依赖关系
- **避免循环**: 设计时避免循环依赖
- **最小依赖**: 只声明必要的依赖关系

### 4. 错误处理

- **分级处理**: 区分关键步骤和可选步骤
- **合理重试**: 为不稳定的步骤设置重试
- **清理资源**: 确保异常情况下的资源清理

### 5. 参数设计

- **默认值**: 为常用参数设置合理默认值
- **参数验证**: 在步骤中验证参数有效性
- **文档化**: 为重要参数添加说明

## 调试和故障排除

### 常见问题

1. **依赖循环**
   ```
   错误: Circular dependency detected: step_a -> step_b -> step_a
   ```
   解决: 重新设计步骤依赖关系，消除循环

2. **参数引用错误**
   ```
   错误: Step 'step_b' not found in parameter reference
   ```
   解决: 检查步骤名称拼写和依赖声明

3. **条件表达式错误**
   ```
   错误: Invalid condition expression: {{ invalid_syntax
   ```
   解决: 检查Jinja2语法和变量引用

### 调试技巧

1. **使用场景可视化**
   ```bash
   dact show-scenario onnx-to-atc-conversion
   ```

2. **检查参数渲染**
   - 查看执行日志中的渲染命令
   - 使用调试模式查看参数值

3. **分步执行**
   - 创建简化版本的场景
   - 逐步添加复杂性

4. **日志分析**
   - 检查 `tmp/` 目录中的步骤日志
   - 关注参数传递和依赖解析

## 参考资料

- [工具定义指南](tool_definition_guide.md)
- [测试用例编写指南](case_writing_guide.md)
- [端到端测试指南](../e2e_testing_guide.md)
- [API参考文档](../api_reference.md)