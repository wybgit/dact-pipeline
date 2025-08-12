# DACT VSCode Extension

This extension provides comprehensive support for DACT (Davinci AI Chip/Compiler Test Pipeline) files in Visual Studio Code.

## Features

### 🎨 Syntax Highlighting
- **Tool files** (`.tool.yml`): Highlights DACT-specific keywords like `command_template`, `post_exec`, `parameters`
- **Scenario files** (`.scenario.yml`): Highlights scenario structure including `steps`, `depends_on`, `condition`
- **Case files** (`.case.yml`): Highlights test case definitions and parameter overrides
- **Jinja2 templates**: Special highlighting for `{{ steps.*.outputs.* }}` template expressions

### 📝 Code Snippets
Comprehensive snippets for rapid development:

#### Tool Snippets
- `dact-tool` - Basic tool definition
- `dact-tool-advanced` - Advanced tool with validation and retry logic
- `dact-python-tool` - Python-based tool definition
- `dact-param` - Tool parameter definition
- `dact-output` - Post-execution output definition

#### Scenario Snippets  
- `dact-scenario` - Basic scenario definition
- `dact-scenario-advanced` - Advanced scenario with dependencies and cleanup
- `dact-step` - Individual scenario step
- `dact-step-conditional` - Conditional step with retry logic

#### Case Snippets
- `dact-case` - Basic test case definition
- `dact-case-advanced` - Advanced case with validation and setup/teardown
- `dact-case-data-driven` - Data-driven test case
- `dact-validation` - Validation rule definition

#### Template Snippets
- `jinja-steps` - Reference step outputs: `{{ steps.step_name.outputs.output_name }}`
- `jinja-case` - Reference case parameters: `{{ case.param_name }}`

### 🚀 Commands
- **DACT: Run this test file** - Execute the current DACT file
  - For `.case.yml` files: Runs `dact filename.case.yml`
  - For `.scenario.yml` files: Shows scenario pipeline with `dact show-scenario`
  - For `.tool.yml` files: Lists available tools with `dact list-tools`
- **DACT: Validate this file** - Validate YAML syntax and structure

### 🎯 Smart Features
- **Auto-completion**: Intelligent suggestions for DACT keywords and properties
- **Context menus**: Right-click on DACT files to access commands
- **File type detection**: Automatic language detection for `.tool.yml`, `.scenario.yml`, `.case.yml`
- **Bracket matching**: Auto-closing pairs for YAML structures
- **Comment support**: Line comments with `#`

## Installation

### From Source
1. Clone the repository
2. Open the `dact-vscode-extension` folder in VSCode
3. Press `F5` to launch a new Extension Development Host window
4. The extension will be active in the new window

### Package Installation
1. Run `vsce package` in the extension directory to create a `.vsix` file
2. Install using `code --install-extension dact-vscode-*.vsix`

## Usage

### Creating Tool Definitions
1. Create a new file with `.tool.yml` extension
2. Type `dact-tool` and press Tab to insert a basic tool template
3. Customize the tool definition with your specific parameters

```yaml
name: my-tool
description: Tool description
type: shell
command_template: echo '{{ message }}'
parameters:
  message:
    type: str
    required: true
    default: "Hello World"
    help: "Message to display"
post_exec:
  outputs:
    result: "find_file(dir='.', pattern='*.log')"
```

### Creating Scenarios
1. Create a new file with `.scenario.yml` extension  
2. Type `dact-scenario` and press Tab to insert a scenario template
3. Add steps and configure parameter flow

```yaml
name: my-scenario
description: Scenario description
steps:
  - name: step1
    tool: my-tool
    params:
      message: "Step 1"
  - name: step2
    tool: another-tool
    depends_on: ["step1"]
    params:
      input: "{{ steps.step1.outputs.result }}"
```

### Creating Test Cases
1. Create a new file with `.case.yml` extension
2. Type `dact-case` and press Tab to insert a case template
3. Configure test parameters and validation

```yaml
cases:
  - name: my-test-case
    description: "Test case description"
    scenario: my-scenario
    params:
      step1:
        message: "Override value"
    validation:
      - type: output
        target: "result"
        expected: "expected_value"
```

### Running Tests
- **Command Palette**: Press `Ctrl+Shift+P` and type "DACT: Run this test file"
- **Context Menu**: Right-click on a DACT file and select "DACT: Run this test file"
- **Keyboard**: Use the configured keyboard shortcut (if set)

## Configuration

The extension automatically detects DACT files based on their extensions:
- `.tool.yml` → `dact-tool` language
- `.scenario.yml` → `dact-scenario` language  
- `.case.yml` → `dact-case` language

## Requirements

- Visual Studio Code 1.80.0 or higher
- DACT CLI tool installed and available in PATH

## Extension Settings

This extension contributes the following settings:
- File associations for DACT file types
- Syntax highlighting rules
- Code snippet definitions
- Command palette entries

## Known Issues

- Jinja2 template validation is basic and may not catch all syntax errors
- Complex YAML structures may not be perfectly highlighted
- Command execution requires DACT CLI to be properly installed

## Release Notes

### 0.0.1
- Initial release
- Basic syntax highlighting for all DACT file types
- Comprehensive code snippets
- Run and validate commands
- Auto-completion support
- Context menu integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the extension thoroughly
5. Submit a pull request

## License

This extension is part of the DACT project and follows the same license terms.