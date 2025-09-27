# Information_Extractor

A python project built with best practices, featuring clean architecture, dependency injection, and comprehensive testing.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **UV** - Fast Python package manager and virtual environment management  
- **Loguru** - Structured logging with excellent performance
- **Pydantic Settings** - Type-safe configuration management with environment variable support
- **Clean Architecture** - Separation of concerns with organized code structure
- **Database Services** - Pre-built connectors for MSSQL, Oracle, and Teradata
- **LLM Integration** - Chat and batch processing services for AI/ML workflows
- **Prompt Management** - Template system for managing AI prompts
- **Pytest Setup** - Testing framework with example tests
- **SOC & OOP Principles** - Separation of concerns and object-oriented design patterns

## Project Structure

```
information_extractor/
├── app/
│   └── api/v1/endpoints/    # API route definitions
├── data/                    # Data files and datasets
├── docs/                    # Project documentation
├── src/
│   ├── cli/                 # Command-line interface modules
│   ├── core/                # Core functionality (config, logging)
│   └── services/            # Business logic services
│       ├── database/        # Database connection services
│       ├── llm/            # LLM integration services
│       └── prompt/         # Prompt management services
├── tests/                   # Test files and test utilities
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore patterns
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # This file
```

## Quick Start

1. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your actual configuration values
```

2. **Create and activate virtual environment:**
```bash
uv venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
uv pip install -e .
```

4. **Run the application:**
```bash
python main.py
```

## Configuration

Edit the `.env` file to configure:

- **LLM Services**: MODEL, UDAL_PAT, BASE_URL, endpoints
- **Database Connections**: Teradata, MSSQL, Oracle credentials
- **API Settings**: Project name, API versioning

## Development Workflow

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/config/test_config.py -v
```


### Adding New Services
1. Create service module in `src/services/`
2. Add configuration settings to `src/core/config.py`
3. Create corresponding tests in `tests/`
4. Update documentation

### Database Services
Pre-built database services are available for:
- **MSSQL**: `src/services/database/mssql_db_service.py`
- **Oracle**: `src/services/database/oracle_db_service.py` 
- **Teradata**: `src/services/database/teradata_db_service.py`

### LLM Integration
- **Chat Service**: `src/services/llm/llm_service_soc.py`
- **Prompt Management**: `src/services/prompt/prompt_manager.py`
- **Templates**: `src/services/prompt/templates.py`

## About the Project Generator

This project was created using the Python Project Generator, a scaffolding tool designed to:

- **Accelerate Development**: Skip boilerplate setup and focus on business logic
- **Enforce Best Practices**: Built-in patterns for clean, maintainable code
- **Provide Production-Ready Structure**: Logging, configuration, testing, and deployment ready
- **Support Multiple Use Cases**: API development, data processing, AI/ML workflows
- **Maintain Consistency**: Standardized project structure across teams

### Generator Repository
The project generator source code and documentation can be found at: `[Your Repository URL]`

### Generating New Projects
To create additional projects using the same scaffold:

```bash
python project_generator.py <new_project_name>
```

