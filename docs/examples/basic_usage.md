# 基础使用示例

本文档提供了 DACT Pipeline 的基础使用示例，帮助您快速上手。

## 示例 1: 简单的工具调用

### 创建工具定义

首先创建一个简单的工具定义文件：

```yaml
# tools/echo-tool.tool.yml
name: echo-tool
type: shell
description: "简单的回显工具"
command_template: 'echo "{{ message }}"'

parameters:
  message:
    type: str
    required: true
    default: "Hello, DACT!"
    help: "要输出的消息"

success_pattern: "Hello"
timeout: 30
```

### 创建测试用例

创建一个测试用例来使用这个工具：

```yaml
# cases/echo_test.case.yml
cases:
  - name: test_echo_basic
    description: "基础回显测试"
    tool: echo-tool
    params:
      message: "Hello, World!"
    
    validation:
      - type: exit_code
        expected: 0
        description: "命令应该成功执行"
      
      - type: stdout_contains
        patterns: ["Hello, World!"]
        description: "输出应该包含指定消息"

  - name: test_echo_default
    description: "使用默认参数的回显测试"
    tool: echo-tool
    # 不指定参数，使用默认值
    
    validation:
      - type: exit_code
        expected: 0
      - type: stdout_contains
        patterns: ["Hello, DACT!"]
```

### 运行测试

```bash
# 运行测试
dact cases/echo_test.case.yml

# 查看详细输出
dact cases/echo_test.case.yml -v

# 生成 HTML 报告
dact cases/echo_test.case.yml --html=report.html
```

## 示例 2: 文件处理工具

### 创建文件处理工具

```yaml
# tools/file-processor.tool.yml
name: file-processor
type: shell
description: "文件处理工具"
command_template: |
  {% if operation == 'copy' %}
  cp "{{ input_file }}" "{{ output_file }}"
  {% elif operation == 'move' %}
  mv "{{ input_file }}" "{{ output_file }}"
  {% elif operation == 'count' %}
  wc -l "{{ input_file }}" > "{{ output_file }}"
  {% endif %}

parameters:
  operation:
    type: str
    required: true
    choices: ["copy", "move", "count"]
    help: "要执行的操作"
  
  input_file:
    type: str
    required: true
    help: "输入文件路径"
  
  output_file:
    type: str
    required: true
    help: "输出文件路径"

timeout: 60

post_exec:
  outputs:
    result_file: "{{ output_file }}"
    file_size: "get_file_size(path='{{ output_file }}')"
```

### 创建测试用例

```yaml
# cases/file_processing.case.yml
common_params:
  input_file: "test_data/sample.txt"
  output_dir: "outputs"

cases:
  - name: test_file_copy
    description: "测试文件复制功能"
    tool: file-processor
    
    setup:
      create_dirs: ["test_data", "outputs"]
      copy_files:
        - src: "/dev/null"
          dst: "test_data/sample.txt"
      commands:
        - "echo 'Line 1\nLine 2\nLine 3' > test_data/sample.txt"
    
    params:
      operation: "copy"
      output_file: "{{ output_dir }}/copied_file.txt"
    
    validation:
      - type: exit_code
        expected: 0
      
      - type: file_exists
        target: "{{ output_dir }}/copied_file.txt"
        description: "复制的文件应该存在"
      
      - type: file_size
        target: "{{ output_dir }}/copied_file.txt"
        min_value: 1
        description: "复制的文件应该有内容"
    
    teardown:
      preserve_files: ["*.txt"]

  - name: test_line_count
    description: "测试行数统计功能"
    tool: file-processor
    
    setup:
      create_dirs: ["test_data", "outputs"]
      commands:
        - "echo -e 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5' > test_data/sample.txt"
    
    params:
      operation: "count"
      output_file: "{{ output_dir }}/line_count.txt"
    
    validation:
      - type: exit_code
        expected: 0
      
      - type: file_exists
        target: "{{ output_dir }}/line_count.txt"
      
      - type: stdout_contains
        patterns: ["5"]  # 应该有5行
        description: "行数统计应该正确"
```

### 运行文件处理测试

```bash
# 运行所有文件处理测试
dact cases/file_processing.case.yml

# 只运行复制测试
dact cases/file_processing.case.yml -k "copy"

# 查看测试输出
ls -la outputs/
cat outputs/copied_file.txt
cat outputs/line_count.txt
```

## 示例 3: 多步骤场景

### 创建数据处理场景

```yaml
# scenarios/data_pipeline.scenario.yml
name: data-processing-pipeline
description: "数据处理管道示例"
version: "1.0"

default_params:
  input_dir: "data/input"
  output_dir: "data/output"
  temp_dir: "data/temp"

steps:
  - name: prepare_data
    tool: file-processor
    description: "准备输入数据"
    params:
      operation: "copy"
      input_file: "{{ input_dir }}/raw_data.txt"
      output_file: "{{ temp_dir }}/prepared_data.txt"

  - name: process_data
    tool: file-processor
    description: "处理数据"
    depends_on: ["prepare_data"]
    params:
      operation: "count"
      input_file: "{{ steps.prepare_data.outputs.result_file }}"
      output_file: "{{ temp_dir }}/processed_data.txt"

  - name: finalize_results
    tool: file-processor
    description: "整理最终结果"
    depends_on: ["process_data"]
    params:
      operation: "copy"
      input_file: "{{ steps.process_data.outputs.result_file }}"
      output_file: "{{ output_dir }}/final_results.txt"

cleanup_steps:
  - name: cleanup_temp
    tool: file-cleaner
    params:
      directory: "{{ temp_dir }}"
      pattern: "*.txt"
```

### 创建场景测试用例

```yaml
# cases/data_pipeline_test.case.yml
cases:
  - name: test_complete_pipeline
    description: "完整数据处理管道测试"
    scenario: data-processing-pipeline
    
    setup:
      create_dirs: ["data/input", "data/output", "data/temp"]
      commands:
        - "echo -e 'Data line 1\nData line 2\nData line 3' > data/input/raw_data.txt"
    
    params:
      input_dir: "data/input"
      output_dir: "data/output"
      temp_dir: "data/temp"
    
    validation:
      - type: exit_code
        expected: 0
        description: "整个管道应该成功执行"
      
      - type: file_exists
        target: "data/output/final_results.txt"
        description: "最终结果文件应该存在"
      
      - type: file_size
        target: "data/output/final_results.txt"
        min_value: 1
        description: "结果文件应该有内容"
    
    teardown:
      cleanup_dirs: ["data/temp"]
      preserve_files: ["data/output/*.txt"]

  - name: test_pipeline_with_custom_input
    description: "使用自定义输入的管道测试"
    scenario: data-processing-pipeline
    
    setup:
      create_dirs: ["custom/input", "custom/output", "custom/temp"]
      commands:
        - "seq 1 10 > custom/input/raw_data.txt"  # 生成1-10的数字
    
    params:
      input_dir: "custom/input"
      output_dir: "custom/output"
      temp_dir: "custom/temp"
    
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "custom/output/final_results.txt"
    
    teardown:
      cleanup_dirs: ["custom"]
```

### 运行场景测试

```bash
# 运行完整的管道测试
dact cases/data_pipeline_test.case.yml

# 查看场景结构
dact show-scenario data-processing-pipeline

# 查看执行结果
ls -la data/output/
cat data/output/final_results.txt
```

## 示例 4: 参数化测试

### 创建参数化测试用例

```yaml
# cases/parameterized_test.case.yml
# 数据驱动的参数化测试
data_driven_cases:
  - template:
      name: "test_echo_message_{{ item.test_id }}"
      description: "测试消息: {{ item.message }}"
      tool: echo-tool
      params:
        message: "{{ item.message }}"
      validation:
        - type: exit_code
          expected: 0
        - type: stdout_contains
          patterns: ["{{ item.expected_output }}"]
    
    data:
      - test_id: "simple"
        message: "Hello"
        expected_output: "Hello"
      
      - test_id: "with_spaces"
        message: "Hello World"
        expected_output: "Hello World"
      
      - test_id: "with_numbers"
        message: "Test 123"
        expected_output: "Test 123"
      
      - test_id: "special_chars"
        message: "Test!@#$%"
        expected_output: "Test!@#$%"

# 传统的多用例测试
cases:
  - name: test_file_operations_batch
    description: "批量文件操作测试"
    tool: file-processor
    
    setup:
      create_dirs: ["batch_test"]
      commands:
        - "echo 'test content' > batch_test/source.txt"
    
    # 使用循环参数
    parameterized:
      parameters:
        operation: ["copy", "count"]
        suffix: ["_v1", "_v2"]
      combinations: "all"  # 生成所有组合
    
    params:
      input_file: "batch_test/source.txt"
      output_file: "batch_test/result_{{ operation }}{{ suffix }}.txt"
    
    validation:
      - type: exit_code
        expected: 0
      - type: file_exists
        target: "batch_test/result_{{ operation }}{{ suffix }}.txt"
```

### 运行参数化测试

```bash
# 运行所有参数化测试
dact cases/parameterized_test.case.yml

# 运行特定的参数化测试
dact cases/parameterized_test.case.yml -k "simple"

# 查看生成的测试用例
dact list-cases --file cases/parameterized_test.case.yml
```

## 示例 5: 错误处理和重试

### 创建不稳定的工具

```yaml
# tools/unstable-tool.tool.yml
name: unstable-tool
type: shell
description: "模拟不稳定的工具（随机失败）"
command_template: |
  # 随机失败的脚本
  if [ $((RANDOM % 3)) -eq 0 ]; then
    echo "Success: {{ message }}"
    exit 0
  else
    echo "Error: Random failure" >&2
    exit 1
  fi

parameters:
  message:
    type: str
    required: true
    help: "成功时输出的消息"

success_pattern: "Success:"
failure_pattern: "Error:"
timeout: 30
```

### 创建重试测试用例

```yaml
# cases/retry_test.case.yml
cases:
  - name: test_with_retry
    description: "测试重试机制"
    tool: unstable-tool
    
    # 配置重试
    retry_count: 5
    retry_delay: 1
    
    params:
      message: "This should eventually succeed"
    
    validation:
      - type: exit_code
        expected: 0
        description: "最终应该成功"
      
      - type: stdout_contains
        patterns: ["Success:"]
        description: "输出应该包含成功信息"
    
    timeout: 300  # 给足够的时间进行重试

  - name: test_failure_handling
    description: "测试失败处理"
    tool: unstable-tool
    
    # 不重试，期望失败
    retry_count: 0
    
    params:
      message: "This might fail"
    
    validation:
      # 这个测试可能成功也可能失败，我们接受两种结果
      - type: exit_code
        expected: [0, 1]  # 接受成功或失败
        description: "接受成功或失败的结果"
```

### 运行重试测试

```bash
# 运行重试测试（可能需要多次运行才能看到重试效果）
dact cases/retry_test.case.yml -v

# 查看详细的重试日志
cat tmp/test_with_retry/*/stderr.log
```

## 示例 6: 环境变量和条件执行

### 创建环境感知的工具

```yaml
# tools/env-aware-tool.tool.yml
name: env-aware-tool
type: shell
description: "环境感知的工具"
command_template: |
  echo "Environment: $TEST_ENV"
  echo "Debug mode: $DEBUG_MODE"
  {% if enable_feature %}
  echo "Feature enabled: {{ feature_name }}"
  {% endif %}
  echo "Message: {{ message }}"

parameters:
  message:
    type: str
    required: true
    help: "要输出的消息"
  
  enable_feature:
    type: bool
    required: false
    default: false
    help: "是否启用特殊功能"
  
  feature_name:
    type: str
    required: false
    default: "default_feature"
    help: "功能名称"

timeout: 30
```

### 创建条件执行测试

```yaml
# cases/conditional_test.case.yml
cases:
  - name: test_development_env
    description: "开发环境测试"
    tool: env-aware-tool
    
    # 设置环境变量
    setup:
      environment:
        TEST_ENV: "development"
        DEBUG_MODE: "true"
    
    params:
      message: "Development test"
      enable_feature: true
      feature_name: "dev_feature"
    
    validation:
      - type: exit_code
        expected: 0
      - type: stdout_contains
        patterns: ["Environment: development", "Debug mode: true", "Feature enabled: dev_feature"]

  - name: test_production_env
    description: "生产环境测试"
    tool: env-aware-tool
    
    # 条件执行：仅在特定条件下运行
    condition: "{{ env.get('RUN_PROD_TESTS', 'false') == 'true' }}"
    
    setup:
      environment:
        TEST_ENV: "production"
        DEBUG_MODE: "false"
    
    params:
      message: "Production test"
      enable_feature: false
    
    validation:
      - type: exit_code
        expected: 0
      - type: stdout_contains
        patterns: ["Environment: production", "Debug mode: false"]
      - type: stdout_not_contains
        patterns: ["Feature enabled:"]

  - name: test_feature_toggle
    description: "功能开关测试"
    tool: env-aware-tool
    
    # 根据环境变量决定参数
    params:
      message: "Feature toggle test"
      enable_feature: "{{ env.get('ENABLE_FEATURE', 'false') == 'true' }}"
      feature_name: "{{ env.get('FEATURE_NAME', 'default') }}"
    
    validation:
      - type: exit_code
        expected: 0
```

### 运行条件测试

```bash
# 运行开发环境测试
dact cases/conditional_test.case.yml -k "development"

# 启用生产环境测试
RUN_PROD_TESTS=true dact cases/conditional_test.case.yml -k "production"

# 启用功能开关测试
ENABLE_FEATURE=true FEATURE_NAME=custom_feature dact cases/conditional_test.case.yml -k "feature_toggle"
```

## 总结

这些基础示例展示了 DACT Pipeline 的核心功能：

1. **简单工具调用**: 最基本的工具定义和使用
2. **文件处理**: 处理文件操作和验证
3. **多步骤场景**: 复杂的工作流编排
4. **参数化测试**: 数据驱动的批量测试
5. **错误处理**: 重试机制和失败处理
6. **条件执行**: 环境感知和条件控制

通过这些示例，您可以：

- 理解 DACT Pipeline 的基本概念
- 学习如何定义工具、场景和测试用例
- 掌握参数传递和模板渲染
- 了解验证规则和错误处理
- 实践数据驱动测试和条件执行

更多高级功能请参考：
- [高级场景示例](advanced_scenarios.md)
- [自定义工具开发](custom_tools.md)
- [数据驱动测试](data_driven_testing.md)