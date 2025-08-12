# 如何定义场景

场景定义了一个标准化的、由多个步骤组成的测试工作流。它通过编排工具的执行顺序和设定默认参数，来固化一套测试逻辑。

## 1. 创建场景文件

每个场景都在一个独立的 `*.scenario.yml` 文件中定义。我们推荐将所有场景文件存放在项目根目录下的 `scenarios/` 文件夹中。

## 2. 文件结构

一个典型的场景文件结构如下：

```yaml
# scenarios/my-scenario.scenario.yml

# (必须) 场景的唯一名称，用于在用例中引用
name: my-scenario

# (可选) 场景的详细描述
description: "一个先创建文件，然后读取文件内容的标准流程。"

# (必须) 定义该场景包含的所有步骤
steps:
  # 第一个步骤
  - name: create_file_step # 步骤的唯一名称
    tool: create-file      # 该步骤要调用的工具名称
    params:                # 为该步骤的工具传递的参数
      filename: "default_name.txt"

  # 第二个步骤
  - name: read_file_step
    tool: read-file
    params:
      # 这里是依赖传递的核心！
      # 使用 Jinja2 语法引用上一步的输出变量
      input_file: "{{ steps.create_file_step.outputs.output_file }}"
```

## 3. 关键字段说明

-   `name`: 场景的唯一标识符。
-   `steps`: 一个列表，定义了该场景的所有步骤。步骤会**严格按照其在列表中的顺序执行**。
-   `steps.name`: 步骤的唯一名称。这个名称非常重要，因为后续步骤需要通过它来引用该步骤的输出。
-   `steps.tool`: 要调用的工具的名称，必须与 `tools/` 目录中某个工具的 `name` 对应。
-   `steps.params`: 为该步骤的工具设置参数。
    -   **默认值:** 您可以在这里为参数提供一个默认值。
    -   **依赖传递:** 您可以使用 `{{ steps.<前序步骤名>.outputs.<输出变量名> }}` 的语法来引用任何在它之前执行过的步骤所暴露出的输出变量。

通过将工具调用逻辑和依赖关系固化在场景中，测试人员在编写用例时，就可以从繁琐的流程控制中解放出来，只需专注于提供业务数据即可。
