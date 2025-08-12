# DACT Pipeline 文档

本目录包含 DACT Pipeline 项目的完整文档。

## 文档结构

```
docs/
├── index.md                    # 文档首页
├── getting_started.md          # 快速开始指南
├── e2e_testing_guide.md       # 端到端测试指南
├── guides/                     # 详细指南
│   ├── tool_definition_guide.md
│   ├── scenario_definition_guide.md
│   └── case_writing_guide.md
├── api/                        # API 参考文档
│   ├── modules.md
│   ├── models.md
│   ├── tools.md
│   ├── scenarios.md
│   ├── execution.md
│   └── validation.md
├── development/                # 开发指南
│   └── contributing.md
├── examples/                   # 示例和教程
│   └── basic_usage.md
├── _static/                    # 静态资源
│   └── custom.css
├── conf.py                     # Sphinx 配置
├── requirements.txt            # 文档构建依赖
├── Makefile                    # 构建脚本 (Unix)
├── make.bat                    # 构建脚本 (Windows)
├── build_docs.py              # Python 构建脚本
└── README.md                   # 本文件
```

## 构建文档

### 方法 1: 使用 Python 脚本（推荐）

```bash
# 安装依赖并构建 HTML 文档
python build_docs.py --install-deps --clean

# 构建并启动本地服务器
python build_docs.py --serve

# 构建所有格式的文档
python build_docs.py --format all --clean

# 构建英文版本
python build_docs.py --language en
```

### 方法 2: 使用 Make

```bash
# Unix/Linux/Mac
make html

# Windows
make.bat html

# 清理构建文件
make clean

# 实时预览（需要安装 sphinx-autobuild）
make livehtml
```

### 方法 3: 直接使用 Sphinx

```bash
# 安装依赖
pip install -r requirements.txt

# 构建 HTML 文档
sphinx-build -b html . _build/html

# 构建 PDF 文档
sphinx-build -b latex . _build/latex
cd _build/latex && pdflatex dact-pipeline.tex
```

## 查看文档

构建完成后，可以通过以下方式查看文档：

### HTML 版本
- 本地文件：打开 `_build/html/index.html`
- 本地服务器：运行 `python build_docs.py --serve`

### PDF 版本
- 文件位置：`_build/latex/dact-pipeline.pdf`

### EPUB 版本
- 文件位置：`_build/epub/dact-pipeline.epub`

## 文档编写指南

### 文件格式

- 主要使用 Markdown 格式（`.md` 文件）
- 支持 MyST 扩展语法
- API 文档使用 reStructuredText 格式

### 文档规范

1. **标题层级**
   ```markdown
   # 一级标题
   ## 二级标题
   ### 三级标题
   #### 四级标题
   ```

2. **代码块**
   ```markdown
   ```python
   # Python 代码示例
   def example():
       pass
   ```
   
   ```yaml
   # YAML 配置示例
   name: example
   type: shell
   ```
   
   ```bash
   # Shell 命令示例
   dact --help
   ```

3. **交叉引用**
   ```markdown
   参考 [工具定义指南](guides/tool_definition_guide.md)
   ```

4. **警告和提示**
   ```markdown
   ```{note}
   这是一个提示信息
   ```
   
   ```{warning}
   这是一个警告信息
   ```

### 添加新文档

1. 在相应目录下创建 `.md` 文件
2. 在 `index.md` 中添加到 toctree
3. 更新相关的交叉引用
4. 重新构建文档

### API 文档

API 文档使用 Sphinx 的 autodoc 扩展自动生成：

```rst
.. automodule:: dact.models
   :members:
   :undoc-members:
   :show-inheritance:
```

## 文档部署

### GitHub Pages

1. 构建文档：
   ```bash
   python build_docs.py --clean
   ```

2. 将 `_build/html` 内容推送到 `gh-pages` 分支

### 其他平台

- **Read the Docs**: 支持自动构建和部署
- **GitLab Pages**: 使用 `.gitlab-ci.yml` 配置
- **Netlify**: 支持静态站点部署

## 常见问题

### 构建失败

1. **依赖缺失**
   ```bash
   pip install -r requirements.txt
   ```

2. **编码问题**
   - 确保所有文件使用 UTF-8 编码
   - 检查 `conf.py` 中的语言设置

3. **交叉引用错误**
   - 检查文件路径是否正确
   - 确保被引用的文件存在

### 中文支持

1. **字体问题**
   - 安装中文字体
   - 配置 LaTeX 中文支持

2. **PDF 构建失败**
   - 安装 XeLaTeX
   - 配置中文字体路径

### 性能优化

1. **构建速度**
   - 使用增量构建
   - 排除不必要的文件

2. **文档大小**
   - 优化图片大小
   - 压缩静态资源

## 贡献文档

欢迎贡献文档改进！请参考：

1. [贡献指南](development/contributing.md)
2. 提交 Pull Request 前请确保：
   - 文档构建成功
   - 链接和引用正确
   - 遵循文档规范

## 联系我们

如果您在文档使用过程中遇到问题，请：

- 提交 GitHub Issue
- 参与 GitHub Discussions
- 联系项目维护者