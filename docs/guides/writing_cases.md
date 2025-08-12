# 如何编写用例

测试用例是驱动 `dact-pipeline` 执行的入口。它将一个测试场景与具体的测试数据相结合，并可以覆盖场景中预设的默认参数。

## 1. 创建用例文件

用例定义在一个或多个 `*.case.yml` 文件中。您可以根据业务逻辑将相关的用例组织在同一个文件里。

## 2. 文件结构

一个典型的用例文件结构如下：

```yaml
# cases/my_test_cases.case.yml

# (可选) 为该文件下的所有用例定义通用参数
# common_params:
#   soc_version: "Ascend910"

# (必须) 一个包含一个或多个测试用例的列表
cases:
  # 第一个测试用例
  - name: test_case_001 # 用例的唯一名称，将显示在测试报告中
    description: "使用场景的默认参数进行测试"
    scenario: my-scenario # （必须）指定要运行的场景名称

  # 第二个测试用例
  - name: test_case_002
    description: "覆盖场景中的参数进行测试"
    scenario: my-scenario
    params: # （可选）覆盖场景中定义的参数
      # 覆盖 'create_file_step' 步骤的 'filename' 参数
      create_file_step:
        filename: "case_002_specific_name.txt"

  # 第三个测试用例：不使用场景，直接调用工具
  - name: simple_tool_test
    description: "直接调用单个工具进行简单测试"
    tool: my-tool # 直接指定工具名称
    params:
      message: "A direct tool call from a case"

  # 第四个测试用例：包含验证点
  - name: test_with_validation
    scenario: my-scenario
    validation: # (可选) 定义测试成功后需要执行的检查
      - type: file_exists # 检查类型
        path: "tmp/test_with_validation/create_file_step/default_name.txt" # 要检查的文件路径
      - type: log_contains
        file: "tmp/test_with_validation/read_file_step/stdout.log"
        pattern: "default message"
```

## 3. 关键字段说明

-   `cases`: 核心字段，一个列表，其中每一项都是一个独立的测试用例。
-   `cases.name`: 测试用例的名称，它会成为 `pytest` 报告中的测试名。
-   `cases.scenario`: 指定该用例要运行的场景。这是最常用的方式。
-   `cases.tool`: 当您只想做一个简单的、单步的测试时，可以不通过场景，直接指定一个工具来运行。
-   `cases.params`: **参数覆盖**。这是 `dact-pipeline` 灵活性和数据驱动思想的核心体现。您可以在这里为场景中的任何步骤的任何参数提供一个新的值，从而用不同的数据驱动同一个标准测试流程。
-   `cases.validation`: (待实现) 定义用例执行成功后的验证点，例如检查某个文件是否存在，或日志中是否包含特定关键字。

通过这种方式，测试人员可以将测试逻辑（定义在 `scenario` 中）和测试数据（定义在 `case` 中）完全解耦，极大地提高了测试用例的编写效率和可维护性。
