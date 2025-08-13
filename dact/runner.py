from __future__ import annotations

import sys
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment

from dact.logger import console, log
from dact.models import CaseFile, Case, CaseValidation
from dact.tool_loader import load_tools_from_directory
from dact.scenario_loader import load_scenarios_from_directory
from dact.dependency_resolver import DependencyResolver
from dact.validation_engine import ValidationEngine
from dact.executor import Executor


class CaseRunResult:
    def __init__(self, name: str, success: bool, work_dir: Path, errors: Optional[List[str]] = None):
        self.name = name
        self.success = success
        self.work_dir = work_dir
        self.errors = errors or []


def _render_parameters(params: dict, context: dict, jinja_env: Environment) -> dict:
    rendered_params: Dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            template = jinja_env.from_string(value)
            rendered_params[key] = template.render(**context)
        elif isinstance(value, dict):
            rendered_params[key] = _render_parameters(value, context, jinja_env)
        elif isinstance(value, list):
            rendered_list: List[Any] = []
            for item in value:
                if isinstance(item, dict):
                    rendered_list.append(_render_parameters(item, context, jinja_env))
                elif isinstance(item, str):
                    rendered_list.append(jinja_env.from_string(item).render(**context))
                else:
                    rendered_list.append(item)
            rendered_params[key] = rendered_list
        else:
            rendered_params[key] = value
    return rendered_params


def _execute_validations(validation_engine: ValidationEngine, case: Case, work_dir: Path, execution_result: dict):
    if not case.validation:
        return []
    return validation_engine.validate_case(case.validation, execution_result, work_dir)


def _log_section(title: str):
    console.rule(f"{title}")


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    while True:
        if (current / "tools").exists() or (current / "scenarios").exists() or (current / "examples" / "scenarios").exists():
            return current
        if current.parent == current:
            return start
        current = current.parent


def run_case(case: Case, project_root: Path, debug: bool = False) -> CaseRunResult:
    repo_root = _find_project_root(project_root)

    work_dir = repo_root / "dact_outputs" / case.name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    _log_section(f"用例 {case.name}")
    log.info(f"[bold]用例名称[/bold]: [yellow]{case.name}[/yellow]")
    if case.description:
        log.info(f"[bold]描述[/bold]: {case.description}")

    tools = load_tools_from_directory(str(repo_root / "tools"))
    scenarios = load_scenarios_from_directory(str(repo_root / "scenarios"))
    # 同时加载 examples 中的场景（兼容）
    examples = load_scenarios_from_directory(str(repo_root / "examples" / "scenarios"))
    scenarios = {**scenarios, **examples}

    validation_engine = ValidationEngine()
    jinja_env = Environment()

    try:
        # 场景模式
        if case.scenario:
            scenario = scenarios.get(case.scenario)
            if not scenario:
                return CaseRunResult(case.name, False, work_dir, [f"Scenario '{case.scenario}' not found."])

            dep = DependencyResolver()
            errors = dep.validate_dependencies(scenario)
            if errors:
                return CaseRunResult(case.name, False, work_dir, ["Scenario dependency validation failed:"] + errors)

            graph = dep.extract_dependencies(scenario)
            log.info(f"执行顺序: {graph.execution_order}")

            # 构造执行上下文
            run_context: Dict[str, Any] = {"case": {"name": case.name}, "steps": {}}
            if scenario.default_params:
                run_context.update(scenario.default_params)
            if case.params:
                run_context.update(case.params)

            # 执行步骤（含动态执行动画）
            for level in graph.execution_order:
                for step_name in level:
                    step = next((s for s in scenario.steps if s.name == step_name), None)
                    if not step:
                        return CaseRunResult(case.name, False, work_dir, [f"Step '{step_name}' not found in scenario '{scenario.name}'."])

                    _log_section(f"步骤 {step.name}")
                    step_dir = work_dir / step.name
                    step_dir.mkdir(exist_ok=True)

                    tool = tools.get(step.tool)
                    if not tool:
                        return CaseRunResult(case.name, False, work_dir, [f"Tool '{step.tool}' not found for step '{step.name}'."])

                    # 组装参数（场景默认 -> 步骤定义 -> 用例覆盖）
                    params = step.params.copy()
                    if scenario.default_params:
                        for k, v in scenario.default_params.items():
                            if k not in params:
                                params[k] = v
                    if case.params and step.name in case.params:
                        params.update(case.params[step.name])

                    rendered_params = _render_parameters(params, run_context, jinja_env)

                    with console.status(f"正在执行: {tool.name}", spinner="dots"):
                        result = Executor(tool=tool, params=rendered_params).execute(step_dir, debug_mode=debug)

                    run_context["steps"][step.name] = {"outputs": result["outputs"]}

                    if result["returncode"] != 0 and not getattr(step, "continue_on_failure", False):
                        return CaseRunResult(case.name, False, work_dir, [
                            f"Step '{step.name}' failed with exit code {result['returncode']}.",
                            f"Command: {result['command']}"
                        ])

            # 用例级校验
            if case.validation:
                log.info("[bold]用例校验[/bold]…")
                results = _execute_validations(validation_engine, case, work_dir, {"returncode": 0, "outputs": run_context.get("steps", {})})
                failed = [r for r in results if not r.is_valid]
                if failed:
                    return CaseRunResult(case.name, False, work_dir, [r.message for r in failed])

            log.info(f"[bold green]用例 '{case.name}' 执行成功[/bold green]")
            return CaseRunResult(case.name, True, work_dir)

        # 单工具模式
        if case.tool:
            _log_section(f"工具 {case.tool}")
            tool = tools.get(case.tool)
            if not tool:
                return CaseRunResult(case.name, False, work_dir, [f"Tool '{case.tool}' not found."])

            params = case.params or {}
            with console.status(f"正在执行: {tool.name}", spinner="dots"):
                result = Executor(tool=tool, params=params).execute(work_dir, debug_mode=debug)

            if case.validation:
                log.info("[bold]用例校验[/bold]…")
                results = _execute_validations(validation_engine, case, work_dir, result)
                failed = [r for r in results if not r.is_valid]
                if failed:
                    return CaseRunResult(case.name, False, work_dir, [r.message for r in failed])
            elif result["returncode"] != 0:
                return CaseRunResult(case.name, False, work_dir, [
                    f"Command failed with exit code {result['returncode']}",
                    f"Command: {result['command']}"
                ])

            log.info(f"[bold green]用例 '{case.name}' 执行成功[/bold green]")
            return CaseRunResult(case.name, True, work_dir)

        return CaseRunResult(case.name, False, work_dir, ["Case must have either a 'scenario' or a 'tool'."])

    finally:
        # 保留 work_dir 供排查
        pass


def run_case_file(case_file_path: str, debug: bool = False) -> Tuple[List[CaseRunResult], int]:
    case_file = Path(case_file_path)
    if not case_file.exists():
        raise FileNotFoundError(f"{case_file_path} 不存在")

    raw = case_file.read_text(encoding="utf-8")
    import yaml  # lazy import
    data = yaml.safe_load(raw)
    case_file_obj = CaseFile(**data)

    project_root = case_file.resolve().parent
    results: List[CaseRunResult] = []

    # 普通用例
    for case in case_file_obj.cases:
        # 合并 common_params
        if case_file_obj.common_params:
            merged = dict(case_file_obj.common_params)
            merged.update(case.params)
            case.params = merged
        results.append(run_case(case, project_root, debug))

    # 数据驱动用例
    for dd in case_file_obj.data_driven_cases:
        from dact.data_providers import load_test_data
        try:
            test_rows = load_test_data(dd.data_source)
            # 过滤
            if dd.data_filter:
                # 简易过滤：仅支持等值
                filt = dd.data_filter
                filtered = []
                for row in test_rows:
                    ok = True
                    for k, v in filt.items():
                        if row.get(k) != v:
                            ok = False
                            break
                    if ok:
                        filtered.append(row)
                test_rows = filtered
        except Exception as e:
            # 将数据加载错误作为一个失败用例
            case = dd.template.copy(deep=True)
            case.name = f"{dd.template.name}_data_load_error"
            results.append(CaseRunResult(case.name, False, project_root / "dact_outputs" / case.name, [f"Data loading failed: {e}"]))
            continue

        for i, row in enumerate(test_rows):
            case = dd.template.copy(deep=True)
            case.name = dd.name_template or f"{dd.template.name}_{i}"

            # 参数映射
            mapped: Dict[str, Any] = {}
            if dd.parameter_mapping:
                for param_path, data_key in dd.parameter_mapping.items():
                    if data_key in row:
                        if "." in param_path:
                            parts = param_path.split(".")
                            current = mapped
                            for part in parts[:-1]:
                                current = current.setdefault(part, {})
                            current[parts[-1]] = row[data_key]
                        else:
                            mapped[param_path] = row[data_key]
            # 合并到 case.params + common_params
            merged = dict(case_file_obj.common_params)
            merged.update(case.params)
            merged.update(mapped)
            case.params = merged

            results.append(run_case(case, project_root, debug))

    failures = [r for r in results if not r.success]
    return results, (0 if not failures else 1)


def run(target: Optional[str] = None, debug: bool = False, verbose: bool = False) -> int:
    """
    运行指定的用例文件或目录。返回退出码（0 成功，1 失败）。
    """
    if verbose:
        import logging
        log.setLevel(logging.DEBUG if debug else logging.INFO)

    if target is None:
        console.print("[red]请提供要运行的 .case.yml 文件或包含此类文件的目录[/red]")
        return 1

    path = Path(target)
    case_files: List[Path] = []

    if path.is_dir():
        case_files = list(path.glob("**/*.case.yml"))
        if not case_files:
            console.print(f"[yellow]目录中未找到任何 .case.yml 文件: {path}[/yellow]")
            return 0
    else:
        case_files = [path]

    overall_failures: List[Tuple[Path, CaseRunResult]] = []
    for cf in case_files:
        console.rule(f"用例文件 {cf.name}")
        results, exit_code = run_case_file(str(cf), debug=debug)
        for r in results:
            if not r.success:
                overall_failures.append((cf, r))

    # 汇总
    console.rule("汇总")
    if not overall_failures:
        console.print("[bold green]全部用例通过[/bold green]")
        return 0

    for cf, r in overall_failures:
        console.print(f"[red]失败[/red] {cf.name} -> {r.name}")
        for err in r.errors:
            console.print(f"  - {err}")
        console.print(f"  日志目录: {r.work_dir}")
    return 1


