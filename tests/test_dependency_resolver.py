"""
Unit tests for the dependency resolver functionality.
"""
import pytest
from dact.models import Scenario, Step
from dact.dependency_resolver import DependencyResolver, DependencyGraph, DependencyNode


class TestDependencyResolver:
    """Test suite for dependency resolution functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.resolver = DependencyResolver()
    
    def test_extract_implicit_dependencies_from_templates(self):
        """Test extraction of implicit dependencies from Jinja2 templates."""
        step = Step(
            name="test_step",
            tool="test_tool",
            params={
                "input_file": "{{ steps.generate_file.outputs.file_path }}",
                "config": "{{ steps.setup.outputs.config_path }}",
                "static_param": "static_value"
            }
        )
        
        dependencies = self.resolver._extract_template_dependencies(step)
        
        assert "generate_file" in dependencies
        assert "setup" in dependencies
        assert len(dependencies) == 2
    
    def test_extract_explicit_dependencies(self):
        """Test extraction of explicit dependencies from step definition."""
        step = Step(
            name="test_step",
            tool="test_tool",
            depends_on=["step1", "step2"]
        )
        
        scenario = Scenario(
            name="test_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(name="step2", tool="tool2"),
                step
            ]
        )
        
        dependency_graph = self.resolver.extract_dependencies(scenario)
        
        assert "test_step" in dependency_graph.nodes
        assert "step1" in dependency_graph.nodes["test_step"].dependencies
        assert "step2" in dependency_graph.nodes["test_step"].dependencies
    
    def test_combine_explicit_and_implicit_dependencies(self):
        """Test combining explicit and implicit dependencies."""
        step = Step(
            name="test_step",
            tool="test_tool",
            depends_on=["step1"],  # Explicit dependency
            params={
                "input": "{{ steps.step2.outputs.result }}"  # Implicit dependency
            }
        )
        
        scenario = Scenario(
            name="test_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(name="step2", tool="tool2"),
                step
            ]
        )
        
        dependency_graph = self.resolver.extract_dependencies(scenario)
        
        dependencies = dependency_graph.nodes["test_step"].dependencies
        assert "step1" in dependencies
        assert "step2" in dependencies
        assert len(dependencies) == 2
    
    def test_calculate_execution_order_linear(self):
        """Test calculation of execution order for linear dependencies."""
        scenario = Scenario(
            name="linear_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                ),
                Step(
                    name="step3", 
                    tool="tool3",
                    params={"input": "{{ steps.step2.outputs.result }}"}
                )
            ]
        )
        
        dependency_graph = self.resolver.extract_dependencies(scenario)
        
        expected_order = [["step1"], ["step2"], ["step3"]]
        assert dependency_graph.execution_order == expected_order
    
    def test_calculate_execution_order_parallel(self):
        """Test calculation of execution order with parallel steps."""
        scenario = Scenario(
            name="parallel_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(name="step2", tool="tool2"),  # Independent of step1
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
        
        dependency_graph = self.resolver.extract_dependencies(scenario)
        
        # step1 and step2 can run in parallel, step3 depends on both
        assert len(dependency_graph.execution_order) == 2
        assert set(dependency_graph.execution_order[0]) == {"step1", "step2"}
        assert dependency_graph.execution_order[1] == ["step3"]
    
    def test_detect_circular_dependency(self):
        """Test detection of circular dependencies."""
        scenario = Scenario(
            name="circular_scenario",
            steps=[
                Step(
                    name="step1", 
                    tool="tool1",
                    params={"input": "{{ steps.step2.outputs.result }}"}
                ),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                )
            ]
        )
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            self.resolver.extract_dependencies(scenario)
    
    def test_validate_dependencies_success(self):
        """Test successful dependency validation."""
        scenario = Scenario(
            name="valid_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                )
            ]
        )
        
        errors = self.resolver.validate_dependencies(scenario)
        assert len(errors) == 0
    
    def test_validate_dependencies_nonexistent_step(self):
        """Test validation failure for non-existent step reference."""
        scenario = Scenario(
            name="invalid_scenario",
            steps=[
                Step(
                    name="step1", 
                    tool="tool1",
                    params={"input": "{{ steps.nonexistent_step.outputs.result }}"}
                )
            ]
        )
        
        errors = self.resolver.validate_dependencies(scenario)
        assert len(errors) == 1
        assert "nonexistent_step" in errors[0]
    
    def test_get_step_dependencies(self):
        """Test getting dependencies for a specific step."""
        scenario = Scenario(
            name="test_scenario",
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
        
        dependencies = self.resolver.get_step_dependencies(scenario, "step3")
        assert set(dependencies) == {"step1", "step2"}
        
        dependencies = self.resolver.get_step_dependencies(scenario, "step1")
        assert len(dependencies) == 0
    
    def test_get_step_dependents(self):
        """Test getting dependents for a specific step."""
        scenario = Scenario(
            name="test_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                ),
                Step(
                    name="step3", 
                    tool="tool3",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                )
            ]
        )
        
        dependents = self.resolver.get_step_dependents(scenario, "step1")
        assert set(dependents) == {"step2", "step3"}
        
        dependents = self.resolver.get_step_dependents(scenario, "step3")
        assert len(dependents) == 0
    
    def test_generate_mermaid_diagram(self):
        """Test generation of Mermaid diagram."""
        scenario = Scenario(
            name="test_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                )
            ]
        )
        
        diagram = self.resolver.generate_mermaid_diagram(scenario)
        
        assert "graph TD" in diagram
        assert "step1[step1<br/>(tool1)]" in diagram
        assert "step2[step2<br/>(tool2)]" in diagram
        assert "step1 --> step2" in diagram
    
    def test_generate_text_summary(self):
        """Test generation of text summary."""
        scenario = Scenario(
            name="test_scenario",
            steps=[
                Step(name="step1", tool="tool1"),
                Step(
                    name="step2", 
                    tool="tool2",
                    params={"input": "{{ steps.step1.outputs.result }}"}
                )
            ]
        )
        
        summary = self.resolver.generate_text_summary(scenario)
        
        assert "Dependency Analysis for Scenario: test_scenario" in summary
        assert "Execution Order:" in summary
        assert "Step Dependencies:" in summary
        assert "step1 -> no dependencies" in summary
        assert "step2 -> depends on: step1" in summary
    
    def test_complex_dependency_scenario(self):
        """Test a complex scenario with multiple dependency patterns."""
        scenario = Scenario(
            name="complex_scenario",
            steps=[
                Step(name="init", tool="init_tool"),
                Step(name="setup_a", tool="setup_tool"),
                Step(name="setup_b", tool="setup_tool"),
                Step(
                    name="process_a",
                    tool="process_tool",
                    params={
                        "config": "{{ steps.init.outputs.config }}",
                        "input": "{{ steps.setup_a.outputs.data }}"
                    }
                ),
                Step(
                    name="process_b",
                    tool="process_tool",
                    params={
                        "config": "{{ steps.init.outputs.config }}",
                        "input": "{{ steps.setup_b.outputs.data }}"
                    }
                ),
                Step(
                    name="merge",
                    tool="merge_tool",
                    params={
                        "input_a": "{{ steps.process_a.outputs.result }}",
                        "input_b": "{{ steps.process_b.outputs.result }}"
                    }
                )
            ]
        )
        
        dependency_graph = self.resolver.extract_dependencies(scenario)
        
        # Verify execution order
        assert len(dependency_graph.execution_order) == 4
        assert dependency_graph.execution_order[0] == ["init"]
        assert set(dependency_graph.execution_order[1]) == {"setup_a", "setup_b"}
        assert set(dependency_graph.execution_order[2]) == {"process_a", "process_b"}
        assert dependency_graph.execution_order[3] == ["merge"]
        
        # Verify specific dependencies
        assert set(dependency_graph.nodes["process_a"].dependencies) == {"init", "setup_a"}
        assert set(dependency_graph.nodes["process_b"].dependencies) == {"init", "setup_b"}
        assert set(dependency_graph.nodes["merge"].dependencies) == {"process_a", "process_b"}


class TestDependencyGraph:
    """Test suite for DependencyGraph data structure."""
    
    def test_dependency_graph_creation(self):
        """Test creation of dependency graph."""
        nodes = {
            "step1": DependencyNode(name="step1", tool="tool1"),
            "step2": DependencyNode(name="step2", tool="tool2", dependencies=["step1"])
        }
        edges = [("step1", "step2")]
        execution_order = [["step1"], ["step2"]]
        
        graph = DependencyGraph(
            nodes=nodes,
            edges=edges,
            execution_order=execution_order
        )
        
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert len(graph.execution_order) == 2
        assert graph.nodes["step2"].dependencies == ["step1"]


class TestDependencyNode:
    """Test suite for DependencyNode data structure."""
    
    def test_dependency_node_creation(self):
        """Test creation of dependency node."""
        node = DependencyNode(
            name="test_step",
            tool="test_tool",
            description="Test step description",
            dependencies=["dep1", "dep2"]
        )
        
        assert node.name == "test_step"
        assert node.tool == "test_tool"
        assert node.description == "Test step description"
        assert node.dependencies == ["dep1", "dep2"]
    
    def test_dependency_node_default_dependencies(self):
        """Test dependency node with default empty dependencies."""
        node = DependencyNode(name="test_step", tool="test_tool")
        
        assert node.dependencies == []