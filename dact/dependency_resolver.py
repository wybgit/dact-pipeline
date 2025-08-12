"""
Dependency resolution and visualization for DACT scenarios.
"""
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from dact.models import Scenario, Step


@dataclass
class DependencyNode:
    """Represents a step node in the dependency graph."""
    name: str
    tool: str
    description: Optional[str] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class DependencyGraph:
    """Represents the complete dependency graph for a scenario."""
    nodes: Dict[str, DependencyNode]
    edges: List[Tuple[str, str]]  # (from_step, to_step)
    execution_order: List[List[str]]  # Groups of steps that can run in parallel
    
    def __post_init__(self):
        if not self.nodes:
            self.nodes = {}
        if not self.edges:
            self.edges = []
        if not self.execution_order:
            self.execution_order = []


class DependencyResolver:
    """Resolves and analyzes step dependencies in scenarios."""
    
    def __init__(self):
        pass
    
    def extract_dependencies(self, scenario: Scenario) -> DependencyGraph:
        """
        Extract dependency relationships from a scenario.
        
        This method analyzes both explicit dependencies (if defined in step model)
        and implicit dependencies from Jinja2 template references.
        """
        nodes = {}
        edges = []
        
        # Create nodes for each step
        for step in scenario.steps:
            # Check if step has explicit dependencies
            explicit_deps = step.depends_on or []
            
            # Extract implicit dependencies from Jinja2 templates
            implicit_deps = self._extract_template_dependencies(step)
            
            # Combine all dependencies
            all_deps = list(set(explicit_deps + implicit_deps))
            
            nodes[step.name] = DependencyNode(
                name=step.name,
                tool=step.tool,
                description=step.description,
                dependencies=all_deps
            )
            
            # Create edges for dependencies
            for dep in all_deps:
                edges.append((dep, step.name))
        
        # Calculate execution order
        execution_order = self._calculate_execution_order(nodes)
        
        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            execution_order=execution_order
        )
    
    def _extract_template_dependencies(self, step: Step) -> List[str]:
        """
        Extract step dependencies from Jinja2 template references.
        
        Looks for patterns like {{ steps.step_name.outputs.* }} in parameter values.
        """
        import re
        
        dependencies = set()
        
        # Check all parameter values for step references
        for param_value in step.params.values():
            if isinstance(param_value, str):
                # Look for patterns like {{ steps.step_name.outputs.* }}
                matches = re.findall(r'{{\s*steps\.([^.]+)\.', param_value)
                dependencies.update(matches)
        
        return list(dependencies)
    
    def _calculate_execution_order(self, nodes: Dict[str, DependencyNode]) -> List[List[str]]:
        """
        Calculate the execution order using topological sorting.
        
        Returns groups of steps that can be executed in parallel.
        """
        # Create a copy of dependencies for manipulation
        remaining_deps = {}
        for name, node in nodes.items():
            remaining_deps[name] = set(node.dependencies)
        
        execution_order = []
        processed = set()
        
        while remaining_deps:
            # Find steps with no remaining dependencies
            ready_steps = []
            for step_name, deps in remaining_deps.items():
                if not deps:
                    ready_steps.append(step_name)
            
            if not ready_steps:
                # Circular dependency detected
                remaining_steps = list(remaining_deps.keys())
                raise ValueError(f"Circular dependency detected among steps: {remaining_steps}")
            
            # Add ready steps to execution order
            execution_order.append(ready_steps)
            processed.update(ready_steps)
            
            # Remove processed steps from dependencies
            for step_name in ready_steps:
                del remaining_deps[step_name]
            
            # Remove processed steps from other steps' dependencies
            for deps in remaining_deps.values():
                deps -= processed
        
        return execution_order
    
    def validate_dependencies(self, scenario: Scenario) -> List[str]:
        """
        Validate scenario dependencies and return list of error messages.
        """
        errors = []
        step_names = {step.name for step in scenario.steps}
        
        # First check for references to non-existent steps before building dependency graph
        for step in scenario.steps:
            # Check explicit dependencies
            if step.depends_on:
                for dep in step.depends_on:
                    if dep not in step_names:
                        errors.append(f"Step '{step.name}' depends on non-existent step '{dep}'")
            
            # Check implicit dependencies from templates
            implicit_deps = self._extract_template_dependencies(step)
            for dep in implicit_deps:
                if dep not in step_names:
                    errors.append(f"Step '{step.name}' depends on non-existent step '{dep}'")
        
        # Only check for circular dependencies if no missing step references
        if not errors:
            try:
                dependency_graph = self.extract_dependencies(scenario)
                # If we get here without exception, no circular dependencies exist
            except ValueError as e:
                errors.append(str(e))
        
        return errors
    
    def get_step_dependencies(self, scenario: Scenario, step_name: str) -> List[str]:
        """Get direct dependencies for a specific step."""
        dependency_graph = self.extract_dependencies(scenario)
        if step_name in dependency_graph.nodes:
            return dependency_graph.nodes[step_name].dependencies
        return []
    
    def get_step_dependents(self, scenario: Scenario, step_name: str) -> List[str]:
        """Get steps that depend on the specified step."""
        dependency_graph = self.extract_dependencies(scenario)
        dependents = []
        
        for node in dependency_graph.nodes.values():
            if step_name in node.dependencies:
                dependents.append(node.name)
        
        return dependents
    
    def generate_mermaid_diagram(self, scenario: Scenario) -> str:
        """
        Generate a Mermaid diagram representation of the scenario dependencies.
        """
        dependency_graph = self.extract_dependencies(scenario)
        
        lines = ["graph TD"]
        
        # Add nodes
        for node in dependency_graph.nodes.values():
            node_label = f"{node.name}[{node.name}<br/>({node.tool})]"
            lines.append(f"    {node.name}[{node.name}<br/>({node.tool})]")
        
        # Add edges
        for from_step, to_step in dependency_graph.edges:
            lines.append(f"    {from_step} --> {to_step}")
        
        # Add styling for different execution levels
        colors = ["#ff9999", "#99ff99", "#9999ff", "#ffff99", "#ff99ff", "#99ffff"]
        for i, level in enumerate(dependency_graph.execution_order):
            color = colors[i % len(colors)]
            for step in level:
                lines.append(f"    classDef level{i} fill:{color}")
                lines.append(f"    class {step} level{i}")
        
        return "\n".join(lines)
    
    def generate_text_summary(self, scenario: Scenario) -> str:
        """
        Generate a text summary of the scenario dependencies.
        """
        dependency_graph = self.extract_dependencies(scenario)
        
        lines = [f"Dependency Analysis for Scenario: {scenario.name}"]
        lines.append("=" * 50)
        
        # Execution order
        lines.append("\nExecution Order:")
        for i, level in enumerate(dependency_graph.execution_order):
            if len(level) == 1:
                lines.append(f"  Level {i+1}: {level[0]}")
            else:
                lines.append(f"  Level {i+1}: {', '.join(level)} (parallel)")
        
        # Step details
        lines.append("\nStep Dependencies:")
        for node in dependency_graph.nodes.values():
            if node.dependencies:
                deps_str = ", ".join(node.dependencies)
                lines.append(f"  {node.name} -> depends on: {deps_str}")
            else:
                lines.append(f"  {node.name} -> no dependencies")
        
        return "\n".join(lines)