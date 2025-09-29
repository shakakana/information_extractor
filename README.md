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
- **Document Parser** - Advanced PDF parsing with Docling and VLM support
- **Pytest Setup** - Testing framework with example tests
- **SOC & OOP Principles** - Separation of concerns and object-oriented design patterns

## Project Structure

```
information_extractor/
├── app/
│   └── api/v1/endpoints/    # API route definitions
├── data/                    # Data files and datasets
│   └── pdf/                 # PDF documents for processing
├── docs/                    # Project documentation
├── src/
│   ├── cli/                 # Command-line interface modules
│   ├── core/                # Core functionality (config, logging)
│   └── services/            # Business logic services
│       ├── database/        # Database connection services
│       ├── llm/            # LLM integration services
│       ├── parser/         # PDF document parser service
│       └── prompt/         # Prompt management services
│   ├── utils/              # Utilities 
├── tests/                   # Test files and test utilities
├── output/                  # Parsed document outputs (generated)
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
- **Document Parser**: Model paths, VLM settings, GPU/CPU preferences

## Development Workflow

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/config/test_config.py -v

# Run parser tests
pytest tests/services/parser/ -v
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

---

## PDF Document Parser Service

### Overview

The PDF Document Parser Service provides enterprise-grade PDF parsing capabilities using IBM's Docling toolkit with Vision Language Model (VLM) support. Built with type safety (Pydantic v2) and robust logging (Loguru), it handles complex PDFs including scanned documents, multi-language content, and documents with tables and images.

### Key Features

- **Multiple Pipeline Types**
  - **Standard Pipeline**: Traditional OCR + layout analysis with table structure recognition
  - **VLM Pipeline**: Vision Language Models for enhanced accuracy on complex layouts

- **Multiple Output Formats**
  - JSON (structured document representation)
  - Markdown (human-readable format)
  - DocTags (document-native format)
  - Plain Text

- **Vision Language Model Support**
  - SmolDocling (lightweight, fast)
  - Granite Vision (IBM's powerful vision model)
  - Custom HuggingFace VLM models
  - Remote API support (Ollama, LM Studio, watsonx.ai)

- **Advanced Capabilities**
  - OCR for scanned documents
  - Table structure recognition
  - Multi-language support
  - Picture description generation
  - GPU acceleration (CUDA, MPS for Apple Silicon)
  - Model prefetching for offline/air-gapped environments

- **Type-Safe Configuration**
  - Pydantic v2 models for robust validation
  - Environment variable support
  - Easy configuration management

### Installation

Install with document parsing support:

```bash
# Standard installation
uv pip install docling loguru pydantic

# With VLM support
uv pip install "docling[vlm]" loguru pydantic

# For Apple Silicon (MLX acceleration)
uv pip install "docling[vlm]" loguru pydantic
```

### Quick Start Guide

#### 1. Basic Usage (Standard Pipeline)

```python
from src.services.parser.pdf_parser import create_parser, OutputFormat

# Create parser with default settings
parser = create_parser()

# Parse a document
result = parser.parse_document(
    "data/pdf/document.pdf",
    output_formats=[OutputFormat.MARKDOWN, OutputFormat.JSON]
)

if result.success:
    print(f"✅ Parsed in {result.processing_time:.2f}s")
    print(f"📄 Pages: {result.page_count}")
    
    # Access parsed content
    markdown = result.markdown_content
    json_data = result.json_content
```

#### 2. Vision Language Model Pipeline

```python
from src.services.parser.pdf_parser import create_vlm_parser, VlmModel, ResponseFormat

# Use VLM for enhanced accuracy
parser = create_vlm_parser(
    vlm_model=VlmModel.SMOL_DOCLING,
    response_format=ResponseFormat.DOCTAGS
)

result = parser.parse_document("complex_document.pdf")
```

#### 3. Custom Configuration

```python
from src.services.parser.pdf_parser import PDFDocumentParser, ParserConfig, PipelineType

config = ParserConfig(
    pipeline_type=PipelineType.STANDARD,
    enable_ocr=True,
    ocr_languages=["en", "es"],
    enable_table_structure=True,
    num_threads=8,
    use_gpu=True,
    enable_picture_description=True
)

parser = PDFDocumentParser(config)
```

#### 4. Offline/Air-Gapped Environments

```python
# Download models once
parser = create_parser(
    artifacts_path="./models",
    auto_download_models=True
)

# Later, use prefetched models
parser = create_parser(artifacts_path="./models")
```

#### 5. Remote VLM APIs

```python
config = ParserConfig(
    pipeline_type=PipelineType.VLM,
    enable_remote_services=True,
    api_url="http://localhost:11434/v1/chat/completions",
    api_model="granite3.2-vision:latest",
    vlm_prompt="OCR this page to markdown.",
    vlm_response_format=ResponseFormat.MARKDOWN
)

parser = PDFDocumentParser(config)
```

### Configuration Options

#### ParserConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pipeline_type` | PipelineType | STANDARD | Pipeline to use (STANDARD or VLM) |
| `enable_ocr` | bool | True | Enable OCR for scanned content |
| `ocr_languages` | List[str] | ["en"] | OCR language codes |
| `enable_table_structure` | bool | True | Enable table structure recognition |
| `match_table_cells` | bool | True | Match table structure to PDF cells |
| `num_threads` | int | 4 | Number of processing threads (1-16) |
| `use_gpu` | bool | True | Use GPU acceleration if available |
| `artifacts_path` | str | None | Path to prefetched models |
| `auto_download_models` | bool | False | Auto-download models on first run |
| `vlm_model` | VlmModel | SMOL_DOCLING | VLM model to use |
| `vlm_response_format` | ResponseFormat | DOCTAGS | VLM output format |
| `enable_picture_description` | bool | False | Add VLM descriptions to images |
| `enable_remote_services` | bool | False | Enable remote VLM APIs |
| `generate_page_images` | bool | True | Generate page images for VLM |

### Pipeline Types

#### Standard Pipeline
Best for most use cases:
- Traditional OCR with EasyOCR
- Layout analysis with DocLayNet
- Table structure with TableFormer
- Fast and reliable
- Lower resource requirements

```python
parser = create_parser(
    enable_ocr=True,
    enable_table_structure=True
)
```

#### VLM Pipeline
Best for complex layouts:
- Vision Language Models process entire pages
- Better accuracy on challenging documents
- Understands visual context
- Higher resource requirements
- Supports local and remote models

```python
parser = create_vlm_parser(
    vlm_model=VlmModel.GRANITE_VISION,
    response_format=ResponseFormat.MARKDOWN
)
```

### Available VLM Models

| Model | Description | Best For | Framework |
|-------|-------------|----------|-----------|
| SMOL_DOCLING | Lightweight, fast | General documents | Transformers |
| SMOL_DOCLING_MLX | MLX-optimized | Apple Silicon | MLX |
| GRANITE_DOCLING | Balanced accuracy | Complex documents | Transformers |
| GRANITE_DOCLING_MLX | MLX-optimized | Apple Silicon | MLX |
| GRANITE_VISION | High accuracy | Challenging layouts | Transformers |
| CUSTOM | User-defined | Custom needs | Configurable |

### Output Formats

- **JSON**: Structured document with metadata, layout, and content hierarchy
- **Markdown**: Human-readable format with preserved structure
- **DocTags**: Document-native format with precise bounding boxes
- **Text**: Plain text extraction

### Saving Results

```python
from src.services.parser.pdf_parser import save_results_to_files

# Parse document
result = parser.parse_document("document.pdf")

# Save all formats to output directory
save_results_to_files(result, output_dir="output")

# Files created:
# - output/document.md
# - output/document.json
# - output/document.txt
# - output/document.doctags
```

### Performance Tips

1. **GPU Acceleration**: Enable `use_gpu=True` for CUDA or MPS (Apple Silicon)
2. **Threading**: Adjust `num_threads` based on your CPU (4-8 recommended)
3. **Model Selection**: Use SMOL models for speed, GRANITE for accuracy
4. **Batch Processing**: Process multiple documents sequentially
5. **Prefetch Models**: Download models once for offline usage

### Error Handling

```python
result = parser.parse_document("document.pdf")

if result.success:
    # Process successful result
    markdown = result.markdown_content
else:
    # Handle error
    logger.error(f"Parse failed: {result.error_message}")
    logger.info(f"Attempted for {result.processing_time:.2f}s")
```

### Examples

See complete examples in `src/services/parser/pdf_parser.py`:
- Standard pipeline usage
- VLM pipeline configuration
- Remote API integration
- Custom model setup
- Offline model management

### Troubleshooting

**Issue**: Slow processing
- **Solution**: Enable GPU, reduce `num_threads`, use SMOL models

**Issue**: Out of memory
- **Solution**: Reduce `num_threads`, use CPU instead of GPU, process fewer pages

**Issue**: Poor OCR quality
- **Solution**: Check `ocr_languages`, try VLM pipeline, verify image DPI

**Issue**: Table structure incorrect
- **Solution**: Set `match_table_cells=False`, use VLM pipeline

**Issue**: Models not found (offline)
- **Solution**: Run with `auto_download_models=True` once, then use `artifacts_path`

### API Reference

Full API documentation available in code docstrings:
- `PDFDocumentParser`: Main parser class
- `ParserConfig`: Configuration model
- `ParseResult`: Result model with content and metadata
- `create_parser()`: Convenience factory for standard pipeline
- `create_vlm_parser()`: Convenience factory for VLM pipeline
- `save_results_to_files()`: Save parsed content to disk

### Dependencies

Core dependencies:
```
docling>=2.0.0
pydantic>=2.0.0
loguru>=0.7.0
```

Optional dependencies for VLM:
```
transformers>=4.40.0
torch>=2.0.0
mlx>=0.15.0  # For Apple Silicon
```

### License & Attribution

This parser service is built on [IBM Docling](https://github.com/docling-project/docling), an open-source document conversion toolkit released under the MIT license.

- **Docling**: IBM Research, LF AI & Data Foundation
- **Paper**: [Docling Technical Report](https://arxiv.org/abs/2408.09869)

---

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

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Check documentation in `/docs`
- Review example code in `/src/services/parser`

## License

[Your License Here]