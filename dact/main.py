import pytest
import sys
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from dact.inspector import DACTInspector
from dact.__version__ import __version__
from pydantic import ValidationError

def version_callback(value: bool):
    if value:
        console.print(f"DACT Pipeline version {__version__}")
        raise typer.Exit()

app = typer.Typer(help="DACT Pipeline - A data-driven test pipeline for AI chip/compiler")
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
    """运行测试用例"""
    args = []
    
    if test_path:
        args.append(test_path)
    
    # Add any extra arguments passed to the command
    if ctx.args:
        args.extend(ctx.args)
    
    # Custom --resume flag handling
    if resume:
        args.append("--lf")  # --lf is pytest's last-failed flag
    
    if verbose:
        args.append("-v")
    
    if debug:
        args.append("-s")  # Don't capture output in debug mode
    
    # Add our plugin to the command line arguments if it's not already there
    args.extend(["-p", "dact.pytest_plugin"])
    
    console.print(f"[bold blue]Running pytest with arguments:[/bold blue] {args}")
    
    exit_code = pytest.main(args)
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
    """将 YAML 用例转换为 pytest 文件，并进行字段合法性检查。"""
    try:
        from dact.yaml_converter import convert_case_yaml_to_py
        path = convert_case_yaml_to_py(yaml_case, output_py)
        console.print(f"生成成功: {path}")
    except Exception as e:
        console.print(f"[red]转换失败: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def validate(case_file: str = typer.Argument(..., help="需要校验的 .case.yml 文件")):
    """校验 YAML 用例文件格式与必填项。"""
    import yaml
    from pathlib import Path
    from dact.models import CaseFile
    try:
        p = Path(case_file)
        if not p.exists():
            console.print(f"[red]文件不存在: {case_file}[/red]")
            raise typer.Exit(code=2)
        data = yaml.safe_load(p.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or 'cases' not in data:
            console.print("[red]YAML 格式不合法：缺少 'cases'[/red]")
            raise typer.Exit(code=2)
        CaseFile(**data)
        console.print(f"[green]校验通过[/green]: {case_file}")
    except ValidationError as ve:
        console.print("[red]YAML 字段校验失败[/red]")
        for err in ve.errors():
            loc = '.'.join(map(str, err.get('loc', [])))
            msg = err.get('msg', '')
            console.print(f" - {loc}: {msg}")
        raise typer.Exit(code=2)
    except Exception as e:
        console.print(f"[red]校验异常: {e}[/red]")
        raise typer.Exit(code=1)

def main():
    """
    Main CLI entry point for DACT Pipeline.
    """
    # Handle version flag early
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        console.print(f"DACT Pipeline version {__version__}")
        sys.exit(0)
    
    # If no command is provided, default to 'run' command
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and not sys.argv[1] in ['run', 'list-tools', 'show-scenario', 'list-cases', '--help', '--install-completion', '--show-completion', '--version']):
        # Check if the first argument looks like a file path or pytest option
        if len(sys.argv) > 1 and (sys.argv[1].endswith('.yml') or sys.argv[1].startswith('-')):
            # Insert 'run' command at the beginning
            sys.argv.insert(1, 'run')
    
    app()

if __name__ == "__main__":
    main()
