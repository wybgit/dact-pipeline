import * as vscode from 'vscode';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {

    console.log('DACT Support extension is now active!');

    // Register the run file command
    let runFileCommand = vscode.commands.registerCommand('dact-vscode.runFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('No active editor found.');
            return;
        }

        const document = editor.document;
        const fileName = document.fileName;
        const fileExtension = path.extname(fileName);
        const baseName = path.basename(fileName);

        // Check if it's a DACT file
        if (!fileName.endsWith('.case.yml') && !fileName.endsWith('.scenario.yml') && !fileName.endsWith('.tool.yml')) {
            vscode.window.showWarningMessage('This command can only be run on DACT files (.case.yml, .scenario.yml, .tool.yml).');
            return;
        }

        // Save the document if it has unsaved changes
        if (document.isDirty) {
            const saved = await document.save();
            if (!saved) {
                vscode.window.showErrorMessage('Failed to save the file. Please save manually and try again.');
                return;
            }
        }

        // Get or create a terminal
        let terminal = vscode.window.terminals.find(t => t.name === "DACT Run");
        if (!terminal) {
            terminal = vscode.window.createTerminal("DACT Run");
        }
        terminal.show();

        // Determine the appropriate command based on file type
        let command: string;
        if (fileName.endsWith('.case.yml')) {
            command = `dact "${fileName}"`;
        } else if (fileName.endsWith('.scenario.yml')) {
            // For scenario files, we might want to show the scenario pipeline
            command = `dact show-scenario "${baseName.replace('.scenario.yml', '')}"`;
        } else if (fileName.endsWith('.tool.yml')) {
            // For tool files, we might want to list tools or show tool info
            command = `dact list-tools`;
        } else {
            command = `dact "${fileName}"`;
        }

        // Send the command to the terminal
        terminal.sendText(command);
        
        // Show a status message
        vscode.window.showInformationMessage(`Running DACT command for ${baseName}...`);
    });

    // Register a command to validate DACT files
    let validateFileCommand = vscode.commands.registerCommand('dact-vscode.validateFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('No active editor found.');
            return;
        }

        const document = editor.document;
        const fileName = document.fileName;

        // Check if it's a DACT file
        if (!fileName.endsWith('.case.yml') && !fileName.endsWith('.scenario.yml') && !fileName.endsWith('.tool.yml')) {
            vscode.window.showWarningMessage('This command can only be run on DACT files (.case.yml, .scenario.yml, .tool.yml).');
            return;
        }

        // Save the document if it has unsaved changes
        if (document.isDirty) {
            const saved = await document.save();
            if (!saved) {
                vscode.window.showErrorMessage('Failed to save the file. Please save manually and try again.');
                return;
            }
        }

        // Get or create a terminal
        let terminal = vscode.window.terminals.find(t => t.name === "DACT Validate");
        if (!terminal) {
            terminal = vscode.window.createTerminal("DACT Validate");
        }
        terminal.show();

        // Run validation command (this would need to be implemented in the DACT CLI)
        const command = `python -c "import yaml; yaml.safe_load(open('${fileName}'))"`;
        terminal.sendText(command);
        
        vscode.window.showInformationMessage(`Validating ${path.basename(fileName)}...`);
    });

    // Register completion provider for DACT files
    const completionProvider = vscode.languages.registerCompletionItemProvider(
        ['dact-tool', 'dact-scenario', 'dact-case'],
        {
            provideCompletionItems(document: vscode.TextDocument, position: vscode.Position) {
                const completionItems: vscode.CompletionItem[] = [];

                // Get the current line
                const linePrefix = document.lineAt(position).text.substr(0, position.character);

                // Provide completions based on context
                if (document.languageId === 'dact-tool') {
                    completionItems.push(
                        new vscode.CompletionItem('name', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('description', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('type', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('command_template', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('parameters', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('post_exec', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('success_pattern', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('failure_pattern', vscode.CompletionItemKind.Property)
                    );
                } else if (document.languageId === 'dact-scenario') {
                    completionItems.push(
                        new vscode.CompletionItem('name', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('description', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('steps', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('default_params', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('environment', vscode.CompletionItemKind.Property)
                    );
                } else if (document.languageId === 'dact-case') {
                    completionItems.push(
                        new vscode.CompletionItem('cases', vscode.CompletionItemKind.Property),
                        new vscode.CompletionItem('common_params', vscode.CompletionItemKind.Property)
                    );
                }

                // Add Jinja2 template completions
                if (linePrefix.includes('{{')) {
                    completionItems.push(
                        new vscode.CompletionItem('steps.', vscode.CompletionItemKind.Variable),
                        new vscode.CompletionItem('case.', vscode.CompletionItemKind.Variable),
                        new vscode.CompletionItem('outputs.', vscode.CompletionItemKind.Variable)
                    );
                }

                return completionItems;
            }
        },
        '.' // Trigger completion on dot
    );

    context.subscriptions.push(runFileCommand, validateFileCommand, completionProvider);
}

export function deactivate() {}