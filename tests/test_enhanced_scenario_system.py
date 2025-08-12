"""
Integration tests for the enhanced scenario system with dependency management.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from dact.models import Scenario, Step, Case, CaseFile, Tool, ToolParameter
from dact.dependency_resolver import DependencyResolver
from dact.pytest_plugin import TestCaseItem, CaseYAMLFile
from dact.tool_loader import load_tools_from_directory


class TestEnhancedScenarioSystem:
    """Integration tests for the enhanced scenario system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tools_dir = self.temp_dir / "tools"
        self.scenarios_dir = self.temp_dir / "scenarios"
        self.tools_dir.mkdir()
        self.scenarios_dir.mkdir()
        
        # Create sample tools
        self._create_sample_tools()
        
        # Load tools
        self.tools = load_tools_from_directory(str(self.tools_dir))
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def _create_sample_tools(self):
        """Create sample tool definitions for testing."""
        # Tool 1: File generator
        tool1_content = """
name: file-generator
command_template: "echo '{{ content }}' > {{ output_file }}"
post_exec:
  outputs:
    output_file: "find_file(dir='{{ work_dir }}', pattern='*.txt')"
"""
        (self.tools_dir / "file-generator.tool.yml").write_text(tool1_content)
        
        # Tool 2: File processor
        tool2_content = """
name: file-processor
command_template: "cat {{ input_file }} | sed 's/{{ find }}/{{ replace }}/g' > {{ output_file }}"
post_exec:
  outputs:
    processed_file: "find_file(dir='{{ work_dir }}', pattern='processed_*.txt')"
"""
        (self.tools_dir / "file-processor.tool.yml").write_text(tool2_content)
        
        # Tool 3: File validator
        tool3_content = """
name: file-validator
command_template: "test -f {{ file_path }} && echo 'File exists' || echo 'File missing'"
success_pattern: "File exists"
"""
        (self.tools_dir / "file-validator.tool.yml").write_text(tool3_content)
    
    def test_scenario_with_implicit_dependencies(self):
        """Test scenario execution with implicit dependencies from templates."""
        scenario = Scenario(
            name="implicit_deps_scenario",
            default_params={
                "base_content": "Hello World",
                "output_prefix": "test"
            },
            steps=[
                Step(
                    name="generate",
                    tool="file-generator",
                    params={
                        "content": "{{ base_content }}",
                        "output_file": "{{ output_prefix }}_generated.txt"
                    }
                ),
                Step(
                    name="process",
                    tool="file-processor",
                    params={
                        "input_file": "{{ steps.generate.outputs.output_file }}",
                        "find": "World",
                        "replace": "Universe",
                        "output_file": "processed_{{ output_prefix }}.txt"
                    }
                ),
                Step(
                    name="validate",
                    tool="file-validator",
                    params={
                        "file_path": "{{ steps.process.outputs.processed_file }}"
                    }
                )
            ]
        )
        
        # Test dependency extraction
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # Verify dependencies
        assert len(dependency_graph.nodes) == 3
        assert dependency_graph.nodes["generate"].dependencies == []
        assert dependency_graph.nodes["process"].dependencies == ["generate"]
        assert dependency_graph.nodes["validate"].dependencies == ["process"]
        
        # Verify execution order
        expected_order = [["generate"], ["process"], ["validate"]]
        assert dependency_graph.execution_order == expected_order
    
    def test_scenario_with_explicit_dependencies(self):
        """Test scenario execution with explicit dependencies."""
        scenario = Scenario(
            name="explicit_deps_scenario",
            steps=[
                Step(name="init", tool="file-generator"),
                Step(name="setup_a", tool="file-generator"),
                Step(name="setup_b", tool="file-generator"),
                Step(
                    name="process",
                    tool="file-processor",
                    depends_on=["init", "setup_a", "setup_b"]  # Explicit dependencies
                )
            ]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # Verify explicit dependencies
        process_deps = set(dependency_graph.nodes["process"].dependencies)
        assert process_deps == {"init", "setup_a", "setup_b"}
        
        # Verify execution order
        assert len(dependency_graph.execution_order) == 2
        assert set(dependency_graph.execution_order[0]) == {"init", "setup_a", "setup_b"}
        assert dependency_graph.execution_order[1] == ["process"]
    
    def test_scenario_with_mixed_dependencies(self):
        """Test scenario with both explicit and implicit dependencies."""
        scenario = Scenario(
            name="mixed_deps_scenario",
            steps=[
                Step(name="init", tool="file-generator"),
                Step(name="setup", tool="file-generator"),
                Step(
                    name="process",
                    tool="file-processor",
                    depends_on=["init"],  # Explicit dependency
                    params={
                        "input_file": "{{ steps.setup.outputs.output_file }}"  # Implicit dependency
                    }
                )
            ]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # Should have both explicit and implicit dependencies
        process_deps = set(dependency_graph.nodes["process"].dependencies)
        assert process_deps == {"init", "setup"}
    
    def test_scenario_validation_success(self):
        """Test successful scenario validation."""
        scenario = Scenario(
            name="valid_scenario",
            steps=[
                Step(name="step1", tool="file-generator"),
                Step(
                    name="step2",
                    tool="file-processor",
                    params={"input_file": "{{ steps.step1.outputs.output_file }}"}
                )
            ]
        )
        
        resolver = DependencyResolver()
        errors = resolver.validate_dependencies(scenario)
        
        assert len(errors) == 0
    
    def test_scenario_validation_failure(self):
        """Test scenario validation with errors."""
        scenario = Scenario(
            name="invalid_scenario",
            steps=[
                Step(
                    name="step1",
                    tool="file-processor",
                    params={"input_file": "{{ steps.nonexistent.outputs.file }}"}
                )
            ]
        )
        
        resolver = DependencyResolver()
        errors = resolver.validate_dependencies(scenario)
        
        assert len(errors) == 1
        assert "nonexistent" in errors[0]
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        scenario = Scenario(
            name="circular_scenario",
            steps=[
                Step(
                    name="step1",
                    tool="file-processor",
                    params={"input_file": "{{ steps.step2.outputs.file }}"}
                ),
                Step(
                    name="step2",
                    tool="file-processor",
                    params={"input_file": "{{ steps.step1.outputs.file }}"}
                )
            ]
        )
        
        resolver = DependencyResolver()
        errors = resolver.validate_dependencies(scenario)
        
        assert len(errors) == 1
        assert "Circular dependency" in errors[0]
    
    def test_parameter_override_hierarchy(self):
        """Test parameter override hierarchy in scenario execution."""
        scenario = Scenario(
            name="override_scenario",
            default_params={
                "timeout": 30,
                "output_dir": "/tmp/default",
                "format": "txt"
            },
            steps=[
                Step(
                    name="generate",
                    tool="file-generator",
                    params={
                        "timeout": 60,  # Override scenario default
                        "content": "Test content",
                        "output_file": "{{ output_dir }}/test.{{ format }}"
                    }
                )
            ]
        )
        
        case = Case(
            name="test_case",
            scenario="override_scenario",
            params={
                "generate": {
                    "format": "json"  # Override scenario default
                }
            }
        )
        
        # Simulate parameter merging logic from pytest_plugin
        step = scenario.steps[0]
        params_to_render = step.params.copy()
        
        # Apply scenario defaults
        for key, value in scenario.default_params.items():
            if key not in params_to_render:
                params_to_render[key] = value
        
        # Apply case overrides
        if case.params and step.name in case.params:
            params_to_render.update(case.params[step.name])
        
        # Verify parameter hierarchy
        assert params_to_render["timeout"] == 60        # From step (highest priority)
        assert params_to_render["format"] == "json"     # From case override
        assert params_to_render["output_dir"] == "/tmp/default"  # From scenario default
        assert params_to_render["content"] == "Test content"     # From step
    
    def test_mermaid_diagram_generation(self):
        """Test Mermaid diagram generation for scenarios."""
        scenario = Scenario(
            name="diagram_scenario",
            steps=[
                Step(name="init", tool="file-generator"),
                Step(
                    name="process",
                    tool="file-processor",
                    params={"input": "{{ steps.init.outputs.file }}"}
                ),
                Step(
                    name="validate",
                    tool="file-validator",
                    params={"file": "{{ steps.process.outputs.result }}"}
                )
            ]
        )
        
        resolver = DependencyResolver()
        diagram = resolver.generate_mermaid_diagram(scenario)
        
        # Verify diagram structure
        assert "graph TD" in diagram
        assert "init[init<br/>(file-generator)]" in diagram
        assert "process[process<br/>(file-processor)]" in diagram
        assert "validate[validate<br/>(file-validator)]" in diagram
        assert "init --> process" in diagram
        assert "process --> validate" in diagram
    
    def test_text_summary_generation(self):
        """Test text summary generation for scenarios."""
        scenario = Scenario(
            name="summary_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(name="step2", tool="tool2"),
                Step(
                    name="step3",
                    tool="tool3",
                    params={
                        "input1": "{{ steps.step1.outputs.result }}",
                        "input2": "{{ steps.step2.outputs.result }}"
                    }
                )
            ]
        )
        
        resolver = DependencyResolver()
        summary = resolver.generate_text_summary(scenario)
        
        # Verify summary content
        assert "Dependency Analysis for Scenario: summary_scenario" in summary
        assert "Execution Order:" in summary
        assert "Step Dependencies:" in summary
        assert "step1 -> no dependencies" in summary
        assert "step2 -> no dependencies" in summary
        assert "step3 -> depends on: step1, step2" in summary
    
    def test_complex_parallel_execution_order(self):
        """Test complex scenario with multiple parallel execution levels."""
        scenario = Scenario(
            name="complex_scenario",
            steps=[
                # Level 1: Independent initialization steps
                Step(name="init_a", tool="file-generator"),
                Step(name="init_b", tool="file-generator"),
                Step(name="init_c", tool="file-generator"),
                
                # Level 2: Steps depending on level 1
                Step(
                    name="process_ab",
                    tool="file-processor",
                    params={
                        "input1": "{{ steps.init_a.outputs.file }}",
                        "input2": "{{ steps.init_b.outputs.file }}"
                    }
                ),
                Step(
                    name="process_c",
                    tool="file-processor",
                    params={"input": "{{ steps.init_c.outputs.file }}"}
                ),
                
                # Level 3: Final step depending on level 2
                Step(
                    name="finalize",
                    tool="file-validator",
                    params={
                        "file1": "{{ steps.process_ab.outputs.result }}",
                        "file2": "{{ steps.process_c.outputs.result }}"
                    }
                )
            ]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # Verify execution order
        assert len(dependency_graph.execution_order) == 3
        
        # Level 1: All init steps can run in parallel
        level1 = set(dependency_graph.execution_order[0])
        assert level1 == {"init_a", "init_b", "init_c"}
        
        # Level 2: Process steps can run in parallel
        level2 = set(dependency_graph.execution_order[1])
        assert level2 == {"process_ab", "process_c"}
        
        # Level 3: Final step
        level3 = dependency_graph.execution_order[2]
        assert level3 == ["finalize"]
        
        # Verify specific dependencies
        assert set(dependency_graph.nodes["process_ab"].dependencies) == {"init_a", "init_b"}
        assert dependency_graph.nodes["process_c"].dependencies == ["init_c"]
        assert set(dependency_graph.nodes["finalize"].dependencies) == {"process_ab", "process_c"}


class TestScenarioSystemEdgeCases:
    """Test edge cases in the scenario system."""
    
    def test_scenario_with_no_dependencies(self):
        """Test scenario where all steps are independent."""
        scenario = Scenario(
            name="independent_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(name="step2", tool="tool2"),
                Step(name="step3", tool="tool3")
            ]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        # All steps should be in the first execution level
        assert len(dependency_graph.execution_order) == 1
        assert set(dependency_graph.execution_order[0]) == {"step1", "step2", "step3"}
        
        # No dependencies
        for node in dependency_graph.nodes.values():
            assert len(node.dependencies) == 0
    
    def test_scenario_with_single_step(self):
        """Test scenario with only one step."""
        scenario = Scenario(
            name="single_step_scenario",
            steps=[Step(name="only_step", tool="tool1")]
        )
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        assert len(dependency_graph.execution_order) == 1
        assert dependency_graph.execution_order[0] == ["only_step"]
        assert len(dependency_graph.nodes["only_step"].dependencies) == 0
    
    def test_scenario_with_empty_steps(self):
        """Test scenario with no steps."""
        scenario = Scenario(name="empty_scenario", steps=[])
        
        resolver = DependencyResolver()
        dependency_graph = resolver.extract_dependencies(scenario)
        
        assert len(dependency_graph.nodes) == 0
        assert len(dependency_graph.execution_order) == 0
        assert len(dependency_graph.edges) == 0