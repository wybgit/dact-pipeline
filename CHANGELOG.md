# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enhanced tool system with dynamic file finding functionality
- CLI command extensions for listing tools, scenarios, and cases
- Improved scenario system with parameter passing and dependency management
- Enhanced test case system with validation and data-driven support
- Execution result management and logging system improvements
- End-to-end testing scenarios for ONNX to ATC conversion
- VSCode plugin with syntax highlighting and code snippets
- Comprehensive documentation and examples
- Packaging and version control improvements

### Changed
- Upgraded pytest integration with better error handling
- Enhanced executor with tool result validation
- Improved Chinese language support in logging

### Fixed
- Parameter override mechanism in test cases
- File path handling in cross-platform environments
- Jinja2 template rendering for complex parameter passing

## [0.1.0] - 2024-12-08

### Added
- Initial release of DACT-Pipeline
- Basic tool registration and management system
- Scenario-based test orchestration
- Test case definition and execution
- Pytest integration with custom plugin
- Rich text logging system
- Basic CLI interface
- VSCode extension for syntax highlighting
- Core documentation and examples

### Features
- YAML-based tool, scenario, and case definitions
- Jinja2 template support for parameter passing
- Post-execution output extraction
- Working directory management
- HTML test reporting
- Cross-platform support (Windows, Linux, macOS)

### Dependencies
- Python 3.9+
- PyYAML 6.0.2+
- Pydantic 2.11.7+
- Jinja2 3.1.6+
- Typer 0.16.0+
- Rich 14.1.0+
- pytest-html 4.1.1+