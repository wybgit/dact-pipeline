#!/bin/bash

# DACT VSCode Extension Installation Script

set -e

echo "🚀 Installing DACT VSCode Extension..."

# Check if VSCode is installed
if ! command -v code &> /dev/null; then
    echo "❌ VSCode is not installed or not in PATH"
    echo "Please install Visual Studio Code first: https://code.visualstudio.com/"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Please run this script from the dact-vscode-extension directory"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    if command -v npm &> /dev/null; then
        npm install
    else
        echo "❌ npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
fi

# Compile TypeScript
echo "🔨 Compiling TypeScript..."
if command -v tsc &> /dev/null; then
    tsc -p .
else
    echo "⚠️  TypeScript compiler not found. Installing globally..."
    npm install -g typescript
    tsc -p .
fi

# Check if vsce is installed
if ! command -v vsce &> /dev/null; then
    echo "📦 Installing vsce (Visual Studio Code Extension manager)..."
    npm install -g vsce
fi

# Package the extension
echo "📦 Packaging extension..."
vsce package

# Find the generated .vsix file
VSIX_FILE=$(ls *.vsix | head -n 1)

if [ -z "$VSIX_FILE" ]; then
    echo "❌ Failed to create .vsix package"
    exit 1
fi

echo "📦 Generated package: $VSIX_FILE"

# Install the extension
echo "🔧 Installing extension in VSCode..."
code --install-extension "$VSIX_FILE"

echo "✅ DACT VSCode Extension installed successfully!"
echo ""
echo "🎉 Next steps:"
echo "1. Restart VSCode"
echo "2. Open a folder containing DACT files (.tool.yml, .scenario.yml, .case.yml)"
echo "3. Try the following features:"
echo "   - Syntax highlighting should work automatically"
echo "   - Type 'dact-tool' and press Tab for snippets"
echo "   - Right-click on DACT files for context menu commands"
echo "   - Use Ctrl+Shift+P and search for 'DACT' commands"
echo ""
echo "📚 For more information, see the README.md file"