from pathlib import Path
from typing import Optional
import yaml
from dact.models import CaseFile

PY_TEMPLATE = """
import pytest


@pytest.mark.parametrize("case", [
{params}
])
def test_dact_case(case):
    import pytest
    import shutil
    from pathlib import Path
    from dact.tool_loader import load_tools_from_directory
    from dact.scenario_loader import load_scenarios_from_directory
    from dact.executor import Executor
    from dact.dependency_resolver import DependencyResolver
    from dact.validation_engine import ValidationEngine
    from dact.models import CaseValidation

    root = Path(__file__).resolve().parent
    tools = load_tools_from_directory(str(root / "tools"))
    scenarios = load_scenarios_from_directory(str(root / "scenarios"))

    # 基于原始 YAML 语义的最小化运行器
    case_name = case.get("name")
    work_dir = root / "tmp" / case_name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    if case.get("scenario"):
        scenario = scenarios.get(case["scenario"]) or pytest.fail(f"Scenario {case['scenario']} not found")
        from dact.dependency_resolver import DependencyResolver
        dep = DependencyResolver()
        errors = dep.validate_dependencies(scenario)
        if errors:
            pytest.fail("\n".join(errors))

        order = dep.extract_dependencies(scenario).execution_order
        context = {"steps": {}}
        for level in order:
            for step_name in level:
                step = next((s for s in scenario.steps if s.name == step_name), None)
                assert step, f"Step {step_name} missing"
                step_dir = work_dir / step.name
                step_dir.mkdir()
                tool = tools.get(step.tool) or pytest.fail(f"Tool {step.tool} missing")
                params = (step.params or {}).copy()
                if case.get("params") and step.name in case["params"]:
                    params.update(case["params"][step.name])
                result = Executor(tool, params).execute(step_dir)
                context["steps"][step.name] = {"outputs": result["outputs"]}
                if result["returncode"] != 0:
                    pytest.fail(f"Step {step.name} failed: {result['command']}")

        if case.get("validation"):
            validations = [CaseValidation(**v) if isinstance(v, dict) else v for v in case["validation"]]
            results = ValidationEngine().validate_case(validations, {"returncode": 0, "outputs": context["steps"]}, work_dir)
            failed = [r for r in results if not r.is_valid]
            if failed:
                pytest.fail("\n".join([f.message for f in failed]))

    elif case.get("tool"):
        tool = tools.get(case["tool"]) or pytest.fail(f"Tool {case['tool']} missing")
        result = Executor(tool, case.get("params") or {}).execute(work_dir)
        if case.get("validation"):
            validations = [CaseValidation(**v) if isinstance(v, dict) else v for v in case["validation"]]
            results = ValidationEngine().validate_case(validations, result, work_dir)
            failed = [r for r in results if not r.is_valid]
            if failed:
                pytest.fail("\n".join([f.message for f in failed]))
        elif result["returncode"] != 0:
            pytest.fail(f"Tool {case['tool']} failed: {result['command']}")
    else:
        pytest.fail("Case must have scenario or tool")
""".strip()


def _render_params_array(cases: CaseFile) -> str:
    arr = []
    for c in cases.cases:
        arr.append({
            "name": c.name,
            "description": c.description,
            "scenario": c.scenario,
            "tool": c.tool,
            "params": c.params,
            "validation": [v.dict() for v in (c.validation or [])],
        })
    import json
    json_block = ",\n".join([json.dumps(x, ensure_ascii=False) for x in arr])
    return json_block


def convert_case_yaml_to_py(yaml_case: str, output_py: Optional[str] = None) -> str:
    p = Path(yaml_case)
    if not p.exists():
        raise FileNotFoundError(f"{yaml_case} 不存在")
    data = yaml.safe_load(p.read_text(encoding='utf-8'))
    # 结构校验（必填项）
    if not isinstance(data, dict) or 'cases' not in data:
        raise ValueError("YAML 格式不合法：缺少 'cases'")
    case_file = CaseFile(**data)

    params_block = _render_params_array(case_file)
    content = PY_TEMPLATE.replace("{params}", params_block)

    out = Path(output_py) if output_py else p.with_suffix("").with_suffix("")  # strip .case.yml
    if not output_py:
        out = out.with_name(out.name + "_generated_test.py")
    out.write_text(content, encoding='utf-8')
    return str(out)

