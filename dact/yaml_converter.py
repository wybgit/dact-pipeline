from pathlib import Path
from typing import Optional
import re
import yaml
from dact.models import CaseFile


def _slugify(name: str) -> str:
    s = re.sub(r"\W+", "_", name.lower()).strip("_")
    if not s or not s[0].isalpha():
        s = f"case_{s or 'unnamed'}"
    return s


def _py_literal(value):
    """Return a Python-source literal for the given Python object.
    Uses repr() to ensure booleans/None and strings are valid Python literals.
    """
    return repr(value)


def convert_case_yaml_to_py(yaml_case: str, output_py: Optional[str] = None) -> str:
    p = Path(yaml_case)
    if not p.exists():
        raise FileNotFoundError(f"{yaml_case} 不存在")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError("YAML 格式不合法：缺少 'cases'")

    case_file = CaseFile(**data)

    # Header
    lines = []
    lines.append("import pytest")
    lines.append("from pathlib import Path")
    lines.append("from dact.runner import run_case")
    lines.append("from dact.models import Case")
    lines.append("")
    lines.append("# 通用参数（来自 YAML 顶层 common_params）")
    lines.append(f"COMMON_PARAMS = {_py_literal(case_file.common_params or {})}")
    lines.append("")

    # One test function per case
    for c in case_file.cases:
        func_name = f"test_{_slugify(c.name)}"
        case_name_lit = _py_literal(c.name)
        desc_lit = _py_literal(c.description)
        scenario_lit = _py_literal(c.scenario)
        tool_lit = _py_literal(c.tool)
        params_lit = _py_literal(c.params or {})
        validation_lit = _py_literal([v.dict() for v in (c.validation or [])])

        body = []
        body.append(f"def {func_name}():")
        body.append("    root = Path(__file__).resolve().parent")
        body.append("    # 合并通用参数和用例参数")
        body.append("    params = {}.copy()")
        body.append("    params.update(COMMON_PARAMS or {})")
        body.append(f"    params.update({params_lit})")
        body.append("    case = Case(")
        body.append(f"        name={case_name_lit},")
        body.append(f"        description={desc_lit},")
        body.append(f"        scenario={scenario_lit},")
        body.append(f"        tool={tool_lit},")
        body.append("        params=params,")
        body.append(f"        validation={validation_lit},")
        body.append("    )")
        body.append("    result = run_case(case, root, debug=False)")
        body.append("    if not result.success:")
        body.append("        pytest.fail(f\"Case failed: {case.name}. See logs: {result.work_dir}\", pytrace=False)")
        body.append("")

        lines.extend(body)

    content = "\n".join(lines) + "\n"

    out = Path(output_py) if output_py else p.with_suffix("").with_suffix("")
    if not output_py:
        out = out.with_name(f"test_{out.name}_generated.py")
    out.write_text(content, encoding="utf-8")
    return str(out)

