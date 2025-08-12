# dact-pipeline (Davinci AI Chip/Compiler Test Pipeline)

## 1. 项目背景

随着 AI 芯片与编译器技术的快速发展，测试的复杂度与日俱增。现有的测试脚本普遍存在工具调用逻辑、测试场景定义与测试数据三者紧密耦合的问题，导致复用性差、维护成本高、扩展困难。dact-pipeline (Davinci AI Chip/Compiler Test Pipeline) 旨在构建一个基于 `pytest` 的通用命令行测试框架，通过分层解耦和配置驱动的理念，解决上述痛点。

## 2. 核心目标

- **效率提升 (Efficiency):** 用户仅需关注测试参数和输入数据，即可快速编写和执行测试。
- **高度扩展 (Extensibility):** 标准化的注册机制，轻松集成新的命令行工具、Python 脚本或二进制程序。
- **彻底解耦 (Decoupling):** 实现测试逻辑（如何测）与测试数据（用什么测）的完全分离。
- **流程编排 (Orchestration):** 支持多阶段测试流程的灵活定义，并自动处理阶段间的依赖参数传递。
- **体验增强 (Usability):** 提供 VSCode 插件，实现语法高亮、智能补全、一键执行等功能。
- **专业报告 (Reporting):** 生成富文本日志和可交互的 HTML 测试报告，便于快速定位问题。
- **便捷分发 (Distribution):** 可打包为标准的 Python `pip` 包，实现一键安装部署。

## 3. 快速开始

### 安装

从源码安装：

```bash
pip install .
```

### 基本使用

DACT Pipeline 提供了丰富的命令行接口来管理和执行测试：

#### 运行测试

```bash
# 运行指定的测试用例文件
dact run examples/cases/conv_add.case.yml
# 或者简化形式（自动识别为run命令）
dact examples/cases/conv_add.case.yml

# 运行测试并生成HTML报告
dact run examples/cases/conv_add.case.yml --html=report.html

# 从上次失败处继续执行
dact run examples/cases/conv_add.case.yml --resume

# 详细输出模式
dact run examples/cases/conv_add.case.yml -v

# 调试模式（不捕获输出）
dact run examples/cases/conv_add.case.yml --debug

# 运行所有测试用例
dact run

# 使用pytest的过滤功能
dact run -k "conv_add"

# 并行执行测试（需要安装pytest-xdist）
dact run -n auto
```

#### 管理工具

```bash
# 列出所有注册的工具
dact list-tools

# 查看工具的详细信息，包括参数和命令模板
# 输出包含：工具名称、类型、描述、命令模板、参数列表
```

#### 管理场景

```bash
# 显示场景的pipeline图示和依赖关系
dact show-scenario e2e-onnx-to-atc

# 查看场景的执行步骤和参数传递
dact show-scenario onnx-to-atc

# 显示场景的详细信息，包括：
# - 场景描述和版本信息
# - 执行步骤列表和工具调用
# - 步骤间的依赖关系图
```

#### 管理测试用例

```bash
# 列出所有测试用例
dact list-cases

# 列出指定文件中的测试用例
dact list-cases --file examples/cases/conv_add.case.yml
# 或使用简化形式
dact list-cases -f examples/cases/conv_add.case.yml

# 输出包含：用例名称、描述、关联场景/工具、源文件路径
```

#### 获取帮助

```bash
# 查看主命令帮助
dact --help

# 查看子命令帮助
dact run --help
dact list-tools --help
dact show-scenario --help
dact list-cases --help
```

### 核心概念

DACT Pipeline 采用三层分离的架构设计：

- **工具 (Tools)**: 封装命令行工具、Python脚本或二进制程序，定义在 `*.tool.yml` 文件中
- **场景 (Scenarios)**: 编排多个工具的执行顺序和依赖关系，定义在 `*.scenario.yml` 文件中  
- **用例 (Cases)**: 为场景提供具体的输入参数和验证规则，定义在 `*.case.yml` 文件中

### 第一个测试

1. **切换到示例目录**：
   ```bash
   cd examples
   ```

2. **运行示例测试**：
   ```bash
   dact cases/conv_add.case.yml
   ```

3. **查看结果**：
   - 控制台显示彩色的实时日志
   - `tmp/` 目录包含详细的执行日志和输出文件
   - 可选择生成HTML测试报告

## 4. 文档和示例

### 完整文档

详细的使用指南和API文档请参考：

- [快速开始指南](docs/getting_started.md)
- [工具定义指南](docs/guides/tool_definition_guide.md)
- [场景定义指南](docs/guides/scenario_definition_guide.md)
- [测试用例编写指南](docs/guides/case_writing_guide.md)
- [端到端测试指南](docs/e2e_testing_guide.md)

### 示例项目

`examples/` 目录包含完整的示例项目：

```
examples/
├── tools/                    # 工具定义
│   ├── ai-json-operator.tool.yml
│   └── atc.tool.yml
├── scenarios/               # 场景定义
│   └── onnx_to_atc.scenario.yml
└── cases/                   # 测试用例
    ├── conv_add.case.yml
    ├── e2e_onnx_to_atc.case.yml
    └── comprehensive_e2e_validation.case.yml
```

### 端到端测试示例

项目提供了完整的ONNX到ATC转换测试流程：

```bash
# 运行端到端测试
cd examples
dact cases/e2e_onnx_to_atc.case.yml

# 运行全面验证测试
dact cases/comprehensive_e2e_validation.case.yml
```

## 5. 贡献指南

欢迎贡献代码和文档！请参考以下步骤：

1. Fork 项目仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd dact-pipeline

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 运行端到端测试
python tests/test_e2e_integration.py
```
