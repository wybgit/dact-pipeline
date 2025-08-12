# 如何定义工具

工具是 `dact-pipeline` 的原子操作单元，它封装了一个命令行调用。

## 1. 创建工具文件

每个工具都在一个独立的 `*.tool.yml` 文件中定义。我们推荐将所有工具文件存放在项目根目录下的 `tools/` 文件夹中。

## 2. 文件结构

一个典型的工具文件结构如下：

```yaml
# tools/my-tool.tool.yml

# (必须) 工具的唯一名称，用于在场景中引用
name: my-tool

# (可选) 工具类型，目前支持 'shell' (默认)
type: shell

# (可选) 工具的详细描述
description: "这是一个示例工具，它会打印一条消息。"

# (可选) 定义此工具接受的所有参数
parameters:
  # 参数的名称
  message:
    # (可选) 参数类型，用于校验，默认为 'str'
    type: str
    # (可选) 是否为必需参数，默认为 false
    required: true
    # (可选) 参数的默认值
    default: "default message"
    # (可选) 参数的帮助说明
    help: "要打印的消息内容"

# (必须) 命令的 Jinja2 模板
# 您可以在这里使用 `parameters` 中定义的变量
command_template: >
  echo "{{ message }}"

# (可选) 定义工具执行后的操作
post_exec:
  # 定义输出变量，用于在场景中传递给后续步骤
  outputs:
    # 变量名: 解析规则
    # 下例中，定义一个名为 'output_path' 的变量，
    # 它的值是通过在当前工作目录的 'out' 子目录中查找 *.txt 文件得到的
    output_path: "find_file(dir='out', pattern='*.txt')"
```

## 3. 关键字段说明

-   `name`: 工具的唯一标识符。
-   `parameters`: 定义了工具的输入参数。`dact-pipeline` 会使用这里的信息对用例中的参数进行校验。
-   `command_template`: 这是工具的核心，一个使用 [Jinja2](https://jinja.palletsprojects.com/) 语法的字符串模板。在运行时，框架会用您在 `case` 中提供的参数来渲染这个模板，生成最终要执行的 `shell` 命令。
-   `post_exec.outputs`: 这是实现步骤间依赖传递的关键。它允许您从当前步骤的执行结果（例如，生成的文件）中提取信息，并将其赋值给一个变量（如 `output_path`），这个变量可以被后续步骤通过 `{{ steps.step_name.outputs.output_path }}` 的语法来引用。
