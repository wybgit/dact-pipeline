# API 模块参考

本节提供 DACT Pipeline 所有模块的详细 API 参考文档。

## 核心模块

```{toctree}
:maxdepth: 2

models
tools
scenarios
execution
validation
```

## 模块概览

### dact.models
定义了 DACT Pipeline 的核心数据模型，包括工具、场景、测试用例等的数据结构。

```{eval-rst}
.. automodule:: dact.models
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.tool_loader
负责工具的加载和管理，包括从 YAML 文件解析工具定义。

```{eval-rst}
.. automodule:: dact.tool_loader
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.scenario_loader
负责场景的加载和管理，包括从 YAML 文件解析场景定义。

```{eval-rst}
.. automodule:: dact.scenario_loader
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.executor
执行引擎，负责工具的实际执行和结果收集。

```{eval-rst}
.. automodule:: dact.executor
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.pytest_plugin
pytest 插件，实现与 pytest 的集成。

```{eval-rst}
.. automodule:: dact.pytest_plugin
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.inspector
检查器模块，提供工具、场景、用例的列表和可视化功能。

```{eval-rst}
.. automodule:: dact.inspector
   :members:
   :undoc-members:
   :show-inheritance:
```

### dact.main
主入口模块，提供命令行接口。

```{eval-rst}
.. automodule:: dact.main
   :members:
   :undoc-members:
   :show-inheritance:
```