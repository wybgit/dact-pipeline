# 工具定义指南

本指南详细介绍如何在 DACT Pipeline 中定义和注册工具。

## 概述

工具 (Tool) 是 DACT Pipeline 的基础组件，用于封装命令行工具、Python脚本或二进制程序。每个工具通过 YAML 配置文件定义，包含参数定义、命令模板、执行验证等信息。

## 工具配置文件结构

工具配置文件使用 `.tool.yml` 扩展名，应放置在 `tools/` 目录下。

### 基本结构

```yaml
name: tool-name                    # 工具名称（必需）
type: shell                        # 工具类型：shell, python, binary
description: "工具描述"             # 工具描述（可选）
command_template: "command {{ param }}"  # 命令模板（必需）
parameters:                        # 参数定义（可选）
  param_name:
    type: str                      # 参数类型
    required: true                 # 是否必需
    default: "default_value"       # 默认值
    help: "参数说明"               # 参数帮助信息
success_pattern: "SUCCESS"         # 成功模式（可选）
failure_pattern: "ERROR"           # 失败模式（可选）
timeout: 300                       # 超时时间（秒）
retry_count: 0                     # 重试次数
post_exec:                         # 后处理配置（可选）
  outputs:
    output_var: "find_file(dir='{{ output_dir }}', pattern='*.txt')"
validation:                        # 验证规则（可选）
  exit_code: 0
  stdout_contains: ["success"]
  stderr_not_contains: ["error"]
```

## 工具类型

### 1. Shell 工具 (type: shell)

最常用的工具类型，用于封装命令行工具。

```yaml
name: ai-json-operator
type: shell
description: "AI JSON Operator 工具，用于生成ONNX模型"
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
post_exec:
  outputs:
    onnx_file: "find_onnx_file(dir='{{ output_dir }}')"
    onnx_dir: "find_onnx_dir(dir='{{ output_dir }}')"
```

### 2. Python 工具 (type: python)

用于封装 Python 脚本或模块。

```yaml
name: data-processor
type: python
description: "数据处理Python脚本"
python_module: "scripts.data_processor"
command_template: "python -m {{ python_module }} --input {{ input_file }} --output {{ output_file }}"
parameters:
  input_file:
    type: str
    required: true
    help: "输入文件路径"
  output_file:
    type: str
    required: true
    help: "输出文件路径"
```

### 3. Binary 工具 (type: binary)

用于封装二进制可执行文件。

```yaml
name: atc
type: binary
description: "ATC模型转换工具"
binary_path: "/usr/local/bin/atc"
command_template: 'atc --framework={{ framework }} --model={{ model }} --input_format={{ input_format }} --output={{ output }} --log={{ log }} --soc_version={{ soc_version }}'
parameters:
  framework:
    type: int
    required: true
    help: "框架类型，5表示ONNX"
  model:
    type: str
    required: true
    help: "模型文件路径"
  input_format:
    type: str
    required: false
    default: "NCHW"
    help: "输入格式"
  output:
    type: str
    required: true
    help: "输出路径"
  log:
    type: str
    required: false
    default: "info"
    help: "日志级别"
  soc_version:
    type: str
    required: true
    help: "SoC版本"
success_pattern: "ATC run success"
failure_pattern: "ATC run failed"
timeout: 600
```

## 参数定义

### 参数类型

支持以下参数类型：

- `str`: 字符串类型
- `int`: 整数类型
- `float`: 浮点数类型
- `bool`: 布尔类型
- `list`: 列表类型
- `dict`: 字典类型

### 参数属性

- `type`: 参数类型（必需）
- `required`: 是否必需参数
- `default`: 默认值
- `help`: 参数说明
- `choices`: 可选值列表（仅适用于字符串和数字类型）
- `min_value`/`max_value`: 数值范围（仅适用于数字类型）

```yaml
parameters:
  log_level:
    type: str
    required: false
    default: "info"
    choices: ["debug", "info", "warning", "error"]
    help: "日志级别"
  
  batch_size:
    type: int
    required: false
    default: 32
    min_value: 1
    max_value: 1024
    help: "批处理大小"
  
  enable_optimization:
    type: bool
    required: false
    default: true
    help: "是否启用优化"
```

## 命令模板

命令模板使用 Jinja2 语法，支持参数替换和条件逻辑。

### 基本参数替换

```yaml
command_template: "tool --input {{ input_file }} --output {{ output_file }}"
```

### 条件参数

```yaml
command_template: 'tool {% if verbose %}--verbose{% endif %} {% if debug %}--debug{% endif %} {{ input_file }}'
```

### 循环参数

```yaml
command_template: 'tool {% for item in items %}--item {{ item }} {% endfor %}'
```

### 复杂模板示例

```yaml
command_template: |
  tool --mode {{ mode }}
  {% if input_files %}
    {% for file in input_files %}
    --input "{{ file }}"
    {% endfor %}
  {% endif %}
  {% if optimization_level > 0 %}
    --optimize --level {{ optimization_level }}
  {% endif %}
  --output "{{ output_dir }}"
```

## 后处理配置 (post_exec)

后处理配置用于从工具执行结果中提取输出变量，供后续步骤使用。

### 内置函数

DACT Pipeline 提供了多个内置函数用于文件查找和数据提取：

```python
# 查找文件
find_file(dir, pattern)              # 查找匹配模式的文件
find_latest_file(dir, pattern)       # 查找最新的匹配文件
find_onnx_file(dir, pattern="**/*.onnx")  # 查找ONNX文件
find_onnx_dir(dir)                   # 查找包含ONNX文件的目录

# 文件检查
check_file_exists(path)              # 检查文件是否存在
get_file_size(path)                  # 获取文件大小

# 文本提取
extract_from_stdout(pattern)         # 从标准输出提取内容
extract_from_stderr(pattern)         # 从标准错误提取内容
```

### 使用示例

```yaml
post_exec:
  outputs:
    # 查找生成的ONNX文件
    onnx_file: "find_onnx_file(dir='{{ output_dir }}')"
    
    # 查找最新的日志文件
    log_file: "find_latest_file(dir='logs', pattern='*.log')"
    
    # 从输出中提取模型信息
    model_info: "extract_from_stdout(pattern='Model: (.+)')"
    
    # 检查输出文件是否存在
    output_exists: "check_file_exists(path='{{ output_dir }}/model.om')"
```

## 验证规则

验证规则用于检查工具执行结果是否符合预期。

### 基本验证

```yaml
validation:
  exit_code: 0                       # 期望的退出码
  stdout_contains: ["success", "completed"]  # 标准输出应包含的内容
  stderr_not_contains: ["error", "failed"]   # 标准错误不应包含的内容
  output_files_exist: ["output.txt", "result.json"]  # 应存在的输出文件
```

### 高级验证

```yaml
validation:
  exit_code: 0
  custom_validators:
    - name: "check_model_size"
      function: "validate_model_size"
      params:
        min_size: 1000
        max_size: 1000000
    - name: "check_accuracy"
      function: "validate_accuracy"
      params:
        threshold: 0.95
```

## 错误处理

### 重试机制

```yaml
retry_count: 3                       # 失败时重试3次
retry_delay: 5                       # 重试间隔5秒
retry_on_exit_codes: [1, 2]         # 仅在特定退出码时重试
```

### 超时设置

```yaml
timeout: 300                         # 300秒超时
kill_timeout: 30                     # 强制终止前等待30秒
```

## 最佳实践

### 1. 命名规范

- 使用小写字母和连字符：`ai-json-operator`
- 名称应简洁且具有描述性
- 避免使用特殊字符和空格

### 2. 参数设计

- 为所有参数提供清晰的帮助信息
- 设置合理的默认值
- 使用类型约束和值范围限制

### 3. 命令模板

- 使用引号包围可能包含空格的参数
- 合理使用条件逻辑避免复杂性
- 考虑跨平台兼容性

### 4. 验证规则

- 设置适当的成功/失败模式
- 验证关键输出文件的存在
- 使用自定义验证器处理复杂逻辑

### 5. 文档化

- 提供详细的工具描述
- 为每个参数添加帮助信息
- 包含使用示例和注意事项

## 示例：完整的工具定义

```yaml
name: model-converter
type: shell
description: "通用模型转换工具，支持多种格式转换"
command_template: |
  model-converter 
  --input "{{ input_model }}"
  --output "{{ output_dir }}/{{ output_name }}"
  --format {{ target_format }}
  {% if optimization_level %}--optimize {{ optimization_level }}{% endif %}
  {% if verbose %}--verbose{% endif %}
  {% if custom_config %}--config "{{ custom_config }}"{% endif %}

parameters:
  input_model:
    type: str
    required: true
    help: "输入模型文件路径"
  
  output_dir:
    type: str
    required: false
    default: "outputs"
    help: "输出目录"
  
  output_name:
    type: str
    required: false
    default: "converted_model"
    help: "输出文件名（不含扩展名）"
  
  target_format:
    type: str
    required: true
    choices: ["onnx", "tflite", "tensorrt", "openvino"]
    help: "目标格式"
  
  optimization_level:
    type: int
    required: false
    min_value: 0
    max_value: 3
    help: "优化级别 (0-3)"
  
  verbose:
    type: bool
    required: false
    default: false
    help: "详细输出模式"
  
  custom_config:
    type: str
    required: false
    help: "自定义配置文件路径"

success_pattern: "Conversion completed successfully"
failure_pattern: "Conversion failed"
timeout: 600
retry_count: 2

post_exec:
  outputs:
    converted_model: "find_latest_file(dir='{{ output_dir }}', pattern='{{ output_name }}.*')"
    conversion_log: "find_latest_file(dir='{{ output_dir }}', pattern='*.log')"
    model_size: "get_file_size(path='{{ outputs.converted_model }}')"

validation:
  exit_code: 0
  stdout_contains: ["Conversion completed"]
  output_files_exist: ["{{ output_dir }}/{{ output_name }}.*"]
  custom_validators:
    - name: "validate_model_integrity"
      function: "check_model_format"
      params:
        format: "{{ target_format }}"
```

## 故障排除

### 常见问题

1. **工具未找到**
   - 检查工具是否在系统PATH中
   - 验证binary_path设置是否正确
   - 确认工具具有执行权限

2. **参数渲染错误**
   - 检查Jinja2模板语法
   - 验证参数名称拼写
   - 确认参数类型匹配

3. **后处理函数失败**
   - 检查文件路径和模式
   - 验证输出目录是否存在
   - 确认文件生成时机

4. **验证规则失败**
   - 检查期望值设置
   - 验证模式匹配规则
   - 查看详细的执行日志

### 调试技巧

1. 使用 `--debug` 模式查看详细输出
2. 检查 `tmp/` 目录中的执行日志
3. 使用 `dact list-tools` 验证工具注册
4. 手动执行渲染后的命令进行测试

## 参考资料

- [场景定义指南](scenario_definition_guide.md)
- [测试用例编写指南](case_writing_guide.md)
- [端到端测试指南](../e2e_testing_guide.md)
- [API参考文档](../api_reference.md)