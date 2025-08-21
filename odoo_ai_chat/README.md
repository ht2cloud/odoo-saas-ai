# AI Module Generator Chat for Odoo

This module integrates the AI Module Generator directly into Odoo, providing a chat interface for generating and installing modules from natural language requirements.

## Installation

1. Copy the `odoo_ai_chat` directory to your Odoo addons path
2. Restart your Odoo server
3. Go to Apps and search for "AI Module Generator Chat"
4. Install the module

## Features

- **Chat Interface**: Interactive chat interface within Odoo for describing module requirements
- **Real-time Generation**: Watch modules being created with live progress updates
- **Security Analysis**: Automated security scanning and compliance checking
- **Direct Installation**: Install generated modules immediately in your Odoo instance
- **Session Management**: Track all generation sessions and their status

## Usage

1. Navigate to **AI Module Generator** in the main menu
2. Click **Generate Module** to open the chat interface
3. Describe your module requirements in plain English
4. Watch the real-time progress as your module is generated
5. Review the security analysis results
6. Click **Install Module** to add it to your Odoo instance

## Example Prompts

- "Customer management system with contact tracking"
- "Sales dashboard with lead tracking and revenue reports"
- "Inventory management with barcode scanning" 
- "Project management with task tracking and time logging"

## Technical Details

The module consists of:

- **Controllers**: HTTP endpoints for handling generation requests
- **Models**: Database models for tracking chat sessions
- **JavaScript Widget**: Interactive chat interface
- **Templates**: QWeb templates for the UI
- **CSS**: Styling for the chat interface

The module integrates with the existing `ai_module_generator` package to provide:
- Natural language processing via `NLPParser`
- Code generation via `CodeGenerator`
- Security analysis via `SecurityAnalyzer`
- Odoo integration via `OdooIntegration`

## Dependencies

- Odoo 15.0+
- ai_module_generator package (included in this repository)
- Python dependencies listed in requirements.txt

## Configuration

The module uses the current Odoo instance for module installation. For production use, you may want to configure:

- Odoo connection parameters in the controller
- Addons path for module installation
- Security settings for AI generation

## Support

For issues and feature requests, please use the GitHub repository issue tracker.