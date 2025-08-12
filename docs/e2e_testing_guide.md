# End-to-End Testing Guide
# 端到端测试指南

本指南介绍如何使用DACT Pipeline的端到端测试功能，包括ONNX到ATC转换的完整测试流程。

## 概述

端到端测试功能允许您：
- 测试完整的ONNX生成和ATC转换流程
- 验证动态文件名支持和参数传递
- 执行复杂的多步骤测试场景
- 进行数据驱动的批量测试

## 核心组件

### 1. 测试场景 (Test Scenarios)

主要的端到端测试场景定义在 `scenarios/e2e_onnx_to_atc.scenario.yml`：

```yaml
name: e2e-onnx-to-atc
description: "端到端ONNX生成和ATC转换测试场景"
steps:
  - name: generate_onnx
    tool: ai-json-operator
    description: "生成ONNX模型文件"
    
  - name: convert_atc
    tool: atc
    description: "将ONNX模型转换为ATC格式"
    depends_on: ["generate_onnx"]
    
  - name: validate_output
    tool: file-validator
    description: "验证ATC转换输出文件"
    depends_on: ["convert_atc"]
```

### 2. 工具配置 (Tool Configurations)

#### AI JSON Operator 工具
- 文件: `tools/ai-json-operator.tool.yml`
- 功能: 生成ONNX模型文件
- 支持动态文件名输出

#### ATC 工具
- 文件: `tools/atc.tool.yml`
- 功能: 将ONNX模型转换为ATC格式
- 支持多种SoC版本

#### 文件验证器
- 文件: `tools/file-validator.tool.yml`
- 功能: 验证输出文件的存在和大小

### 3. 测试用例 (Test Cases)

提供了多个层次的测试用例：

#### 基础端到端测试
文件: `examples/cases/e2e_onnx_to_atc.case.yml`
- 基本的Conv Add算子测试
- 复杂的Conv BatchNorm ReLU算子测试
- 动态文件名支持测试
- 错误处理测试

#### 全面验证测试
文件: `examples/cases/comprehensive_e2e_validation.case.yml`
- 完整管道验证
- 参数传递验证
- 性能和超时测试
- 兼容性矩阵测试

#### 简单集成测试
文件: `examples/cases/simple_e2e_integration.case.yml`
- 基本工具链测试
- 文件验证器集成测试
- 参数覆盖测试

## 使用方法

### 1. 运行基础端到端测试

```bash
# 运行所有端到端测试
dact examples/cases/e2e_onnx_to_atc.case.yml

# 运行特定测试用例
dact examples/cases/e2e_onnx_to_atc.case.yml -k "test_conv_add_e2e"

# 运行带详细输出的测试
dact examples/cases/e2e_onnx_to_atc.case.yml -v
```

### 2. 运行全面验证测试

```bash
# 运行全面验证测试
dact examples/cases/comprehensive_e2e_validation.case.yml

# 运行特定的验证测试
dact examples/cases/comprehensive_e2e_validation.case.yml -k "complete_pipeline_validation"
```

### 3. 运行集成测试

```bash
# 运行简单集成测试（不需要外部工具）
dact examples/cases/simple_e2e_integration.case.yml

# 运行Python集成测试
python tests/test_e2e_integration.py
```

### 4. 查看测试结果

测试执行后，结果会保存在 `tmp/` 目录下：

```
tmp/
├── test_conv_add_e2e/
│   ├── generate_onnx/
│   │   ├── stdout.log
│   │   └── stderr.log
│   ├── convert_atc/
│   │   ├── stdout.log
│   │   └── stderr.log
│   └── validate_output/
│       ├── stdout.log
│       └── stderr.log
```

## 关键特性

### 1. 动态文件名支持

系统支持动态生成的文件名和目录结构：

```python
# 自动查找ONNX文件，支持如下结构：
# outputs/Conv_testcase_98bd3f/resources/Conv_testcase_98bd3f.onnx

post_exec:
  outputs:
    onnx_file: "find_onnx_file(dir='{{ output_dir }}')"
    onnx_dir: "find_onnx_dir(dir='{{ output_dir }}')"
```

### 2. 参数传递和模板渲染

支持Jinja2模板语法进行参数传递：

```yaml
steps:
  - name: convert_atc
    tool: atc
    params:
      model: "{{ steps.generate_onnx.outputs.onnx_file }}"  # 使用前一步的输出
      soc_version: "{{ soc_version }}"  # 使用场景参数
```

### 3. 验证规则

支持多种验证规则：

```yaml
validation:
  - type: exit_code
    expected: 0
    description: "工具应该成功执行"
  
  - type: file_exists
    target: "outputs/**/*.onnx"
    description: "应该生成ONNX文件"
  
  - type: file_size
    target: "outputs/**/*.om"
    min_value: 1000
    description: "ATC文件应该有合理大小"
```

### 4. 数据驱动测试

支持数据驱动的批量测试：

```yaml
data_driven_cases:
  - template:
      name: batch_operator_test
      scenario: e2e-onnx-to-atc
      params:
        ops: "{{ ops }}"
        soc_version: "{{ soc_version }}"
    
    data:
      - ops: "Conv Add"
        soc_version: "Ascend310"
      - ops: "Conv BatchNorm"
        soc_version: "Ascend310P3"
```

## 故障排除

### 1. 工具未找到错误

如果遇到工具未找到的错误：

```bash
# 检查工具配置
dact list-tools

# 验证工具路径
which ai-json-operator
which atc
```

### 2. 文件未找到错误

如果遇到ONNX文件未找到的错误：

1. 检查 `ai-json-operator` 工具的输出目录
2. 验证 `find_onnx_file` 函数的搜索模式
3. 查看 `generate_onnx` 步骤的日志文件

### 3. 参数传递错误

如果参数传递不正确：

1. 检查Jinja2模板语法
2. 验证参数名称拼写
3. 查看步骤执行日志中的渲染命令

### 4. 验证失败

如果验证规则失败：

1. 检查预期值是否正确
2. 验证文件路径和模式
3. 查看详细的验证结果日志

## 扩展测试

### 添加新的测试用例

1. 在 `examples/cases/` 目录下创建新的 `.case.yml` 文件
2. 定义测试用例和验证规则
3. 运行测试验证功能

### 添加新的工具

1. 在 `tools/` 目录下创建 `.tool.yml` 配置文件
2. 定义工具参数和命令模板
3. 添加验证规则和post_exec输出

### 创建新的场景

1. 在 `scenarios/` 目录下创建 `.scenario.yml` 文件
2. 定义步骤顺序和依赖关系
3. 配置默认参数和环境变量

## 最佳实践

1. **使用描述性的测试名称**: 便于识别测试目的
2. **添加适当的验证规则**: 确保测试的可靠性
3. **使用标签分类测试**: 便于选择性执行
4. **保持测试独立性**: 避免测试间的相互依赖
5. **定期清理测试输出**: 避免磁盘空间问题

## 参考资料

- [工具配置指南](tool_configuration_guide.md)
- [场景定义指南](scenario_definition_guide.md)
- [测试用例编写指南](test_case_writing_guide.md)
- [API参考文档](api_reference.md)