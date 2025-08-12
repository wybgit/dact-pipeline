# DACT Pipeline 文档

欢迎使用 DACT Pipeline (Davinci AI Chip/Compiler Test Pipeline) 文档！

DACT Pipeline 是一个基于 pytest 的通用命令行测试框架，专为 AI 芯片与编译器测试而设计。通过分层解耦和配置驱动的理念，实现测试逻辑、测试场景与测试数据的完全分离。

## 快速导航

```{toctree}
:maxdepth: 2
:caption: 用户指南

getting_started
guides/tool_definition_guide
guides/scenario_definition_guide
guides/case_writing_guide
e2e_testing_guide
```

```{toctree}
:maxdepth: 2
:caption: API 参考

api/modules
api/models
api/tools
api/scenarios
api/execution
```

```{toctree}
:maxdepth: 2
:caption: 开发指南

development/contributing
development/testing
development/architecture
development/extending
```

```{toctree}
:maxdepth: 1
:caption: 示例和教程

examples/basic_usage
examples/advanced_scenarios
examples/custom_tools
examples/data_driven_testing
```

## 核心特性

- **效率提升**: 用户仅需关注测试参数和输入数据，即可快速编写和执行测试
- **高度扩展**: 标准化的注册机制，轻松集成新的命令行工具、Python 脚本或二进制程序
- **彻底解耦**: 实现测试逻辑（如何测）与测试数据（用什么测）的完全分离
- **流程编排**: 支持多阶段测试流程的灵活定义，并自动处理阶段间的依赖参数传递
- **体验增强**: 提供 VSCode 插件，实现语法高亮、智能补全、一键执行等功能
- **专业报告**: 生成富文本日志和可交互的 HTML 测试报告，便于快速定位问题

## 架构概览

DACT Pipeline 采用三层分离的架构设计：

- **工具层 (Tools)**: 封装命令行工具、Python脚本或二进制程序
- **场景层 (Scenarios)**: 编排多个工具的执行顺序和依赖关系  
- **用例层 (Cases)**: 为场景提供具体的输入参数和验证规则

## 快速开始

### 安装

```bash
pip install dact-pipeline
```

### 基本使用

```bash
# 运行测试用例
dact examples/cases/conv_add.case.yml

# 列出所有工具
dact list-tools

# 显示场景流程
dact show-scenario onnx-to-atc

# 列出测试用例
dact list-cases
```

## 获取帮助

- **GitHub**: [https://github.com/dact-pipeline/dact-pipeline](https://github.com/dact-pipeline/dact-pipeline)
- **问题反馈**: [GitHub Issues](https://github.com/dact-pipeline/dact-pipeline/issues)
- **讨论**: [GitHub Discussions](https://github.com/dact-pipeline/dact-pipeline/discussions)

## 索引和表格

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
