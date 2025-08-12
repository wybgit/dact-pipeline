# 贡献指南

感谢您对 DACT Pipeline 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 报告 Bug
- 提出新功能建议
- 提交代码改进
- 完善文档
- 分享使用经验

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/dact-pipeline/dact-pipeline.git
cd dact-pipeline
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 使用 conda
conda create -n dact-pipeline python=3.8
conda activate dact-pipeline
```

### 3. 安装开发依赖

```bash
# 安装项目及开发依赖
pip install -e ".[dev]"

# 或者分别安装
pip install -e .
pip install pytest pytest-html pytest-cov black flake8 mypy
```

### 4. 验证安装

```bash
# 运行测试
pytest tests/

# 检查代码风格
black --check dact/
flake8 dact/

# 类型检查
mypy dact/
```

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 进行开发

- 遵循现有的代码风格和架构模式
- 为新功能添加相应的测试
- 更新相关文档

### 3. 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_tool_loader.py

# 运行覆盖率测试
pytest --cov=dact tests/

# 运行端到端测试
python tests/test_e2e_integration.py
```

### 4. 代码质量检查

```bash
# 格式化代码
black dact/ tests/

# 检查代码风格
flake8 dact/ tests/

# 类型检查
mypy dact/

# 检查导入顺序
isort dact/ tests/
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: add new feature description"
```

### 6. 推送并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## 代码规范

### 1. Python 代码风格

我们使用以下工具来保持代码质量：

- **Black**: 代码格式化
- **Flake8**: 代码风格检查
- **MyPy**: 类型检查
- **isort**: 导入排序

### 2. 命名规范

- **文件名**: 使用小写字母和下划线，如 `tool_loader.py`
- **类名**: 使用 PascalCase，如 `ToolLoader`
- **函数名**: 使用 snake_case，如 `load_tools_from_directory`
- **常量**: 使用大写字母和下划线，如 `POST_EXEC_FUNCTIONS`

### 3. 文档字符串

使用 Google 风格的文档字符串：

```python
def load_tool_from_file(file_path: str) -> Tool:
    """从文件加载工具定义。
    
    Args:
        file_path: 工具配置文件路径
        
    Returns:
        Tool: 加载的工具对象
        
    Raises:
        FileNotFoundError: 当文件不存在时
        ValidationError: 当配置格式错误时
    """
    pass
```

### 4. 类型注解

所有公共函数和方法都应该有类型注解：

```python
from typing import Dict, List, Optional

def process_data(
    input_data: List[Dict[str, Any]], 
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """处理输入数据。"""
    pass
```

## 测试指南

### 1. 测试结构

```
tests/
├── unit/                   # 单元测试
│   ├── test_models.py
│   ├── test_tool_loader.py
│   └── test_executor.py
├── integration/            # 集成测试
│   ├── test_scenario_execution.py
│   └── test_pytest_plugin.py
├── e2e/                   # 端到端测试
│   └── test_complete_pipeline.py
├── fixtures/              # 测试固件
│   ├── tools/
│   ├── scenarios/
│   └── cases/
└── conftest.py            # pytest 配置
```

### 2. 编写测试

```python
import pytest
from pathlib import Path
from dact.tool_loader import load_tool_from_file

class TestToolLoader:
    """工具加载器测试类。"""
    
    def test_load_valid_tool(self, tmp_path):
        """测试加载有效的工具配置。"""
        # 创建测试配置文件
        tool_config = {
            "name": "test-tool",
            "type": "shell",
            "command_template": "echo {{ message }}"
        }
        
        config_file = tmp_path / "test.tool.yml"
        with open(config_file, 'w') as f:
            yaml.dump(tool_config, f)
        
        # 加载工具
        tool = load_tool_from_file(str(config_file))
        
        # 验证结果
        assert tool.name == "test-tool"
        assert tool.type == "shell"
        assert tool.command_template == "echo {{ message }}"
    
    def test_load_invalid_tool(self, tmp_path):
        """测试加载无效的工具配置。"""
        # 创建无效配置文件
        config_file = tmp_path / "invalid.tool.yml"
        with open(config_file, 'w') as f:
            f.write("invalid yaml content: [")
        
        # 验证异常
        with pytest.raises(ValidationError):
            load_tool_from_file(str(config_file))
```

### 3. 测试固件

```python
# conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_workspace():
    """创建临时工作空间。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        
        # 创建目录结构
        (workspace / "tools").mkdir()
        (workspace / "scenarios").mkdir()
        (workspace / "cases").mkdir()
        
        yield workspace

@pytest.fixture
def sample_tool():
    """创建示例工具。"""
    return Tool(
        name="sample-tool",
        type="shell",
        command_template="echo {{ message }}",
        parameters={
            "message": ToolParameter(
                type="str",
                required=True,
                help="要输出的消息"
            )
        }
    )
```

## 文档贡献

### 1. 文档结构

- **用户指南**: 面向最终用户的使用说明
- **API 参考**: 详细的 API 文档
- **开发指南**: 面向开发者的技术文档
- **示例教程**: 实际使用案例和教程

### 2. 文档格式

我们使用 Markdown 和 reStructuredText 格式：

- **Markdown**: 用于一般文档，如指南和教程
- **reStructuredText**: 用于 API 文档和 Sphinx 集成

### 3. 构建文档

```bash
# 安装文档依赖
pip install -r docs/requirements.txt

# 构建 HTML 文档
cd docs
make html

# 实时预览
make livehtml
```

## 发布流程

### 1. 版本管理

我们使用语义化版本控制：

- **主版本号**: 不兼容的 API 更改
- **次版本号**: 向后兼容的功能添加
- **修订版本号**: 向后兼容的问题修复

### 2. 发布检查清单

- [ ] 所有测试通过
- [ ] 代码质量检查通过
- [ ] 文档已更新
- [ ] CHANGELOG.md 已更新
- [ ] 版本号已更新

### 3. 创建发布

```bash
# 更新版本号
bump2version patch  # 或 minor, major

# 创建标签
git tag v1.0.0

# 推送标签
git push origin v1.0.0

# 构建分发包
python setup.py sdist bdist_wheel

# 上传到 PyPI
twine upload dist/*
```

## 社区准则

### 1. 行为准则

- 尊重所有参与者
- 欢迎新手和不同观点
- 专注于建设性的讨论
- 避免人身攻击和歧视性言论

### 2. 沟通渠道

- **GitHub Issues**: 报告 Bug 和功能请求
- **GitHub Discussions**: 一般讨论和问答
- **Pull Requests**: 代码贡献和审查

### 3. 问题报告

报告 Bug 时请包含：

- 详细的问题描述
- 重现步骤
- 期望行为和实际行为
- 环境信息（操作系统、Python 版本等）
- 相关的日志和错误信息

### 4. 功能请求

提出新功能时请包含：

- 功能的详细描述
- 使用场景和动机
- 可能的实现方案
- 对现有功能的影响

## 获取帮助

如果您在贡献过程中遇到问题，可以通过以下方式获取帮助：

- 查看现有的 Issues 和 Discussions
- 创建新的 Issue 或 Discussion
- 联系项目维护者

感谢您的贡献！