import sys
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pathlib import Path

from dact.inspector import DACTInspector
from dact.__version__ import __version__
from pydantic import ValidationError

def version_callback(value: bool):
    if value:
        console.print(f"DACT Pipeline version {__version__}")
        raise typer.Exit()

app = typer.Typer(
    help="DACT Pipeline - A data-driven test pipeline for AI chip/compiler",
    context_settings={"help_option_names": ["-h", "--help"]}
)
console = Console()

@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="显示版本信息")
):
    """DACT Pipeline - A data-driven test pipeline for AI chip/compiler"""
    pass

@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    test_path: Optional[str] = typer.Argument(None, help="测试文件或目录路径"),
    resume: bool = typer.Option(False, "--resume", help="从上次失败处继续执行"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="详细输出"),
    debug: bool = typer.Option(False, "--debug", help="调试模式"),
):
    """运行测试用例（自定义运行器）"""
    # 注意：为了保持兼容，这里忽略 resume 与 pytest 参数，后续可在自定义运行器实现断点续跑
    from dact.runner import run as custom_run

    if test_path is None and ctx.args:
        # 允许用户把路径直接写在 run 后面
        for a in ctx.args:
            if a.endswith('.yml') or a.endswith('.case.yml') or Path(a).exists():
                test_path = a
                break

    exit_code = custom_run(test_path, debug=debug, verbose=verbose)
    sys.exit(exit_code)

@app.command()
def list_tools(tool_name: Optional[str] = typer.Argument(None, help="工具名（可选，显示详情）")):
    """列出已注册工具；提供工具名显示详情。"""
    inspector = DACTInspector()

    try:
        if tool_name:
            details = inspector.get_tool_details(tool_name)
            console.print(Panel.fit(
                f"[bold]名称[/bold]: {details.name}\n"
                f"[bold]类型[/bold]: {details.type}\n"
                f"[bold]描述[/bold]: {details.description or '无描述'}\n"
                f"[bold]命令模板[/bold]: {details.command_template}",
                title=f"工具详情: {details.name}", border_style="cyan"
            ))

            if details.parameters:
                table = Table(title="参数", show_header=True, header_style="bold magenta")
                table.add_column("名称", style="cyan")
                table.add_column("类型", style="green")
                table.add_column("必填", style="yellow")
                table.add_column("默认值", style="white")
                table.add_column("说明", style="blue")
                for name, meta in details.parameters.items():
                    table.add_row(name, meta.get("type", ""), meta.get("required", ""), meta.get("default", ""), meta.get("help", ""))
                console.print(table)
            return

        tools = inspector.list_tools()
        if not tools:
            console.print("[yellow]No tools found in the tools directory.[/yellow]")
            return

        table = Table(title="已注册工具", show_header=True, header_style="bold magenta")
        table.add_column("名称", style="cyan", no_wrap=True)
        table.add_column("类型", style="green")
        table.add_column("描述", style="yellow")
        for tool in tools:
            table.add_row(
                tool.name,
                tool.type,
                tool.description or "无描述",
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")

@app.command()
def show_scenario(scenario_name: str):
    """显示场景的pipeline图示"""
    inspector = DACTInspector()
    
    try:
        pipeline = inspector.show_scenario_pipeline(scenario_name)
        
        # Display scenario header
        console.print(Panel(
            f"[bold blue]{pipeline.name}[/bold blue]\n{pipeline.description or '无描述'}",
            title="场景信息",
            border_style="blue"
        ))
        
        # Display execution steps
        console.print("\n[bold]执行步骤:[/bold]")
        for i, step in enumerate(pipeline.steps, 1):
            step_text = Text()
            step_text.append(f"{i}. ", style="bold white")
            step_text.append(f"{step['name']}", style="cyan")
            step_text.append(" -> 工具: ", style="white")
            step_text.append(f"{step['tool']}", style="yellow")
            
            console.print(step_text)
            if step['description']:
                console.print(f"   描述: {step['description']}", style="dim")
        
        # Display dependencies
        if pipeline.dependencies:
            console.print("\n[bold]依赖关系:[/bold]")
            for step, deps in pipeline.dependencies.items():
                if deps:
                    console.print(f"[cyan]{step}[/cyan] 依赖于: [yellow]{', '.join(deps)}[/yellow]")
                else:
                    console.print(f"[cyan]{step}[/cyan] 无依赖")
                    
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
    except Exception as e:
        console.print(f"[red]未知错误: {e}[/red]")

@app.command()
def list_cases(case_file: str = typer.Argument(..., help="指定一个 .case.yml 或 pytest .py 文件")):
    """显示指定文件中的用例信息与统计。"""
    inspector = DACTInspector()
    try:
        if not case_file:
            console.print("[red]必须指定文件[/red]")
            raise typer.Exit(code=2)

        from pathlib import Path
        p = Path(case_file)
        if not p.exists():
            console.print(f"[red]文件不存在: {case_file}[/red]")
            raise typer.Exit(code=2)

        if case_file.endswith('.case.yml'):
            cases = inspector.list_cases(case_file)
            table = Table(title=f"{case_file} 用例", show_header=True, header_style="bold magenta")
            table.add_column("名称", style="cyan", no_wrap=True)
            table.add_column("描述", style="green")
            table.add_column("目标", style="yellow")
            for c in cases:
                table.add_row(c.name, c.description or "无描述", c.scenario or c.tool or "未指定")
            console.print(table)
            console.print(f"共 {len(cases)} 条用例")
        elif case_file.endswith('.py'):
            # 简单解析 pytest 文件中以 test_ 开头的函数名
            import re
            content = p.read_text(encoding='utf-8')
            names = re.findall(r"^def (test_[\w_]+)\(", content, flags=re.M)
            table = Table(title=f"{case_file} 用例", show_header=True, header_style="bold magenta")
            table.add_column("pytest 测试函数", style="cyan")
            for n in names:
                table.add_row(n)
            console.print(table)
            console.print(f"共 {len(names)} 条用例")
        else:
            console.print("[red]仅支持 .case.yml 或 .py 文件[/red]")
            raise typer.Exit(code=2)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")

@app.command()
def gen_py(yaml_case: str = typer.Argument(..., help="输入 .case.yml 文件"),
           output_py: Optional[str] = typer.Option(None, "--out", "-o", help="输出 pytest .py 文件路径")):
    """将 YAML 用例转换为独立的 Python 运行脚本，并进行字段合法性检查。"""
    try:
        console.print(f"[bold blue]🔄 YAML 转独立运行脚本[/bold blue]")
        console.print(f"  输入文件: [cyan]{yaml_case}[/cyan]")
        
        from dact.yaml_converter import convert_case_yaml_to_py
        path = convert_case_yaml_to_py(yaml_case, output_py)
        
        console.print(f"  输出文件: [cyan]{path}[/cyan]")
        console.print(f"[bold green]✅ 转换成功[/bold green]")
        console.print(f"\n💡 [bold]使用方法[/bold]:")
        console.print(f"   python {path}")
        console.print(f"   dact run {yaml_case}  # 使用 CLI 直接运行 YAML")
        
    except Exception as e:
        console.print(f"[red]❌ 转换失败: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def validate(case_file: str = typer.Argument(..., help="需要校验的 .case.yml 文件")):
    """校验 YAML 用例文件格式与必填项。"""
    import yaml
    from pathlib import Path
    from dact.models import CaseFile
    from dact.tool_loader import load_tools_from_directory
    from dact.scenario_loader import load_scenarios_from_directory
    
    try:
        console.print(f"[bold blue]🔍 正在校验 YAML 文件[/bold blue]: {case_file}")
        
        p = Path(case_file)
        if not p.exists():
            console.print(f"[red]❌ 文件不存在: {case_file}[/red]")
            raise typer.Exit(code=2)
        
        # Stage 1: YAML 语法校验
        console.print("  📝 [bold]步骤 1: YAML 语法校验[/bold]")
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            console.print(f"[red]❌ YAML 语法错误: {e}[/red]")
            raise typer.Exit(code=2)
        console.print("     ✅ YAML 语法正确")
        
        # Stage 2: 基本结构校验
        console.print("  🏗️  [bold]步骤 2: 基本结构校验[/bold]")
        if not isinstance(data, dict):
            console.print("[red]❌ YAML 文件根节点必须是字典格式[/red]")
            raise typer.Exit(code=2)
        
        if 'cases' not in data:
            console.print("[red]❌ YAML 格式不合法：缺少必填字段 'cases'[/red]")
            console.print("   💡 提示：YAML 文件必须包含 'cases' 字段，格式如下：")
            console.print("   cases:")
            console.print("     - name: test_case_1")
            console.print("       tool: my_tool")
            console.print("       # 或者")
            console.print("       scenario: my_scenario")
            raise typer.Exit(code=2)
        
        if not isinstance(data['cases'], list):
            console.print("[red]❌ 'cases' 字段必须是列表格式[/red]")
            raise typer.Exit(code=2)
        
        if len(data['cases']) == 0:
            console.print("[yellow]⚠️  警告：'cases' 列表为空[/yellow]")
        
        console.print("     ✅ 基本结构正确")
        
        # Stage 3: 数据模型校验
        console.print("  📋 [bold]步骤 3: 数据模型校验[/bold]")
        try:
            case_file_obj = CaseFile(**data)
        except ValidationError as ve:
            console.print("[red]❌ 数据模型校验失败：[/red]")
            for err in ve.errors():
                loc = '.'.join(map(str, err.get('loc', [])))
                msg = err.get('msg', '')
                input_val = err.get('input', '')
                console.print(f"     - 位置: [cyan]{loc}[/cyan]")
                console.print(f"       错误: [red]{msg}[/red]")
                if input_val:
                    console.print(f"       输入值: [dim]{input_val}[/dim]")
                console.print()
            raise typer.Exit(code=2)
        console.print("     ✅ 数据模型校验通过")
        
        # Stage 4: 引用依赖校验
        console.print("  🔗 [bold]步骤 4: 引用依赖校验[/bold]")
        
        # 尝试加载工具和场景
        project_root = p.parent.resolve()
        while project_root.parent != project_root:
            if (project_root / "tools").exists() or (project_root / "scenarios").exists():
                break
            project_root = project_root.parent
        
        tools_dir = project_root / "tools"
        scenarios_dir = project_root / "scenarios"
        
        tools = {}
        scenarios = {}
        
        if tools_dir.exists():
            try:
                tools = load_tools_from_directory(str(tools_dir))
                console.print(f"     📦 加载了 {len(tools)} 个工具")
            except Exception as e:
                console.print(f"[yellow]⚠️  加载工具时出错: {e}[/yellow]")
        
        if scenarios_dir.exists():
            try:
                scenarios = load_scenarios_from_directory(str(scenarios_dir))
                console.print(f"     📦 加载了 {len(scenarios)} 个场景")
            except Exception as e:
                console.print(f"[yellow]⚠️  加载场景时出错: {e}[/yellow]")
        
        # 检查用例中的工具和场景引用
        missing_refs = []
        for i, case in enumerate(case_file_obj.cases):
            case_name = case.name or f"案例 #{i+1}"
            
            if case.tool:
                if case.tool not in tools:
                    missing_refs.append(f"案例 '{case_name}' 引用的工具 '{case.tool}' 不存在")
            
            if case.scenario:
                if case.scenario not in scenarios:
                    missing_refs.append(f"案例 '{case_name}' 引用的场景 '{case.scenario}' 不存在")
            
            if not case.tool and not case.scenario:
                missing_refs.append(f"案例 '{case_name}' 必须指定 'tool' 或 'scenario' 中的一个")
        
        if missing_refs:
            console.print("[red]❌ 引用依赖校验失败：[/red]")
            for ref in missing_refs:
                console.print(f"     - {ref}")
            raise typer.Exit(code=2)
        
        console.print("     ✅ 引用依赖校验通过")
        
        # Stage 5: 汇总信息
        console.print("  📊 [bold]步骤 5: 汇总信息[/bold]")
        console.print(f"     - 用例数量: [cyan]{len(case_file_obj.cases)}[/cyan]")
        
        tool_cases = [c for c in case_file_obj.cases if c.tool]
        scenario_cases = [c for c in case_file_obj.cases if c.scenario]
        
        console.print(f"     - 工具用例: [cyan]{len(tool_cases)}[/cyan]")
        console.print(f"     - 场景用例: [cyan]{len(scenario_cases)}[/cyan]")
        
        if case_file_obj.common_params:
            console.print(f"     - 公共参数: [cyan]{len(case_file_obj.common_params)} 个[/cyan]")
        
        if case_file_obj.data_driven_cases:
            console.print(f"     - 数据驱动用例: [cyan]{len(case_file_obj.data_driven_cases)}[/cyan]")
        
        console.print(f"\n[bold green]✅ 校验通过[/bold green]: {case_file}")
        console.print("   💡 提示：可以使用 'dact gen-py' 命令将此 YAML 文件转换为 pytest 脚本")
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ 校验异常: {e}[/red]")
        raise typer.Exit(code=1)

def main():
    """
    Main CLI entry point for DACT Pipeline.
    """
    # Handle version flag early
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        console.print(f"DACT Pipeline version {__version__}")
        sys.exit(0)
    
    # Handle help flag early to show main help instead of redirecting to run command
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        app()
        return
    
    # If no command is provided, default to 'run' command
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and not sys.argv[1] in ['run', 'list-tools', 'show-scenario', 'list-cases', 'gen-py', 'validate', '--help', '--install-completion', '--show-completion', '--version']):
        # Check if the first argument looks like a file path or pytest option
        if len(sys.argv) > 1 and (sys.argv[1].endswith('.yml') or sys.argv[1].startswith('-') and sys.argv[1] not in ['-h', '--help']):
            # Insert 'run' command at the beginning
            sys.argv.insert(1, 'run')
    
    app()

if __name__ == "__main__":
    main()
