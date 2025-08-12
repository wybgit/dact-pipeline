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
def list_tools():
    """列出所有注册的工具"""
    inspector = DACTInspector()
    
    try:
        tools = inspector.list_tools()
        
        if not tools:
            console.print("[yellow]No tools found in the tools directory.[/yellow]")
            return
        
        table = Table(title="注册的工具列表", show_header=True, header_style="bold magenta")
        table.add_column("工具名称", style="cyan", no_wrap=True)
        table.add_column("类型", style="green")
        table.add_column("描述", style="yellow")
        table.add_column("命令模板", style="white")
        table.add_column("参数", style="blue")
        
        for tool in tools:
            # Format parameters for display
            params_str = ""
            if tool.parameters:
                params_list = [f"{name}: {desc}" for name, desc in tool.parameters.items()]
                params_str = "\n".join(params_list)
            
            table.add_row(
                tool.name,
                tool.type,
                tool.description or "无描述",
                tool.command_template,
                params_str
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
def list_cases(case_file: Optional[str] = typer.Option(None, "--file", "-f", help="指定用例文件")):
    """列出测试用例"""
    inspector = DACTInspector()
    
    try:
        cases = inspector.list_cases(case_file)
        
        if not cases:
            if case_file:
                console.print(f"[yellow]在文件 {case_file} 中未找到测试用例.[/yellow]")
            else:
                console.print("[yellow]未找到任何测试用例文件.[/yellow]")
            return
        
        table = Table(title="测试用例列表", show_header=True, header_style="bold magenta")
        table.add_column("用例名称", style="cyan", no_wrap=True)
        table.add_column("描述", style="green")
        table.add_column("场景/工具", style="yellow")
        table.add_column("源文件", style="blue")
        
        for case in cases:
            execution_target = case.scenario or case.tool or "未指定"
            table.add_row(
                case.name,
                case.description or "无描述",
                execution_target,
                case.source_file
            )
        
        console.print(table)
        
    except FileNotFoundError as e:
        console.print(f"[red]文件未找到: {e}[/red]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")

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
