# Odoo AI Module Generator - Web Demo

This is the web-based demo interface for the Odoo AI Module Generator. It provides a real-time, interactive way to generate Odoo modules from natural language requirements.

## Features

🌐 **Web-Based Interface**
- Modern, responsive chat-style UI
- Real-time progress updates
- Example prompts to get started quickly

🤖 **AI-Powered Generation**
- Natural language requirement parsing
- Automatic module structure generation
- Security analysis and compliance checking

📊 **Real-Time Feedback**
- Live progress updates during generation
- Module statistics (files, models, views)
- Security scoring and issue detection

📦 **Demo Deployment**
- Simulated Odoo instance deployment
- One-click module download
- Ready-to-use module packages

## Quick Start

### Start the Demo Server

```bash
# Using the CLI command
odoo-ai-generator demo

# Or directly with Python
python -m ai_module_generator.demo_server

# With custom host/port
odoo-ai-generator demo --host 0.0.0.0 --port 8080
```

### Open Your Browser

Navigate to: http://localhost:5000

### Try It Out

1. **Click an Example**: Use one of the provided example prompts
2. **Describe Your Module**: Enter your requirements in plain English
3. **Click Generate**: Watch real-time progress as your module is created
4. **Review Results**: See statistics, security analysis, and demo deployment
5. **Download**: Get your complete, ready-to-use Odoo module

## Example Prompts

- "Customer management system with contact tracking"
- "Sales dashboard with lead tracking and revenue reports"
- "Inventory management with barcode scanning"
- "Project management with task tracking and time logging"
- "Employee attendance tracking with reporting"
- "Invoice management with payment tracking"

## Architecture

The demo server uses:
- **Flask** for the web framework
- **WebSockets** for real-time updates (with polling fallback)
- **Background Tasks** for async module generation
- **Temporary Storage** for generated modules
- **Security Analysis** integration

## API Endpoints

- `GET /` - Main demo interface
- `POST /api/generate` - Start module generation
- `GET /api/status/<session_id>` - Get generation status
- `GET /api/download/<session_id>` - Download generated module

## Demo vs Production

This demo interface is designed for demonstration purposes:

- **Demo Mode**: Uses simulated Odoo deployment
- **Production Mode**: Would connect to real Odoo instances
- **Security**: Demo shows security analysis results
- **Downloads**: Generated modules are production-ready

## Customization

The demo can be customized by modifying:
- `templates/demo.html` - UI appearance and behavior
- `demo_server.py` - Server logic and API endpoints
- Example prompts and default settings

## Screenshots

The demo interface includes:
- Clean, modern UI with gradient backgrounds
- Chat-style interaction pattern
- Real-time progress indicators
- Detailed results with statistics
- Security analysis visualization
- Download and deployment options

## Development

For development and testing:

```bash
# Install dependencies
pip install flask flask-socketio

# Run in debug mode
odoo-ai-generator demo --debug

# Check server logs for generation progress
```

The demo server automatically handles:
- Session management
- Background processing
- Progress updates
- Error handling
- File cleanup