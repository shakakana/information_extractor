"""
PDF Document Parser Service using Docling
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import time
from enum import Enum

from pydantic import BaseModel, Field
from loguru import logger
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    VlmPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,
    PictureDescriptionVlmOptions,
)
from docling.datamodel.pipeline_options_vlm_model import (
    HuggingFaceVlmOptions,
    ApiVlmOptions,
    ResponseFormat,
    InferenceFramework,
)
from docling.datamodel import vlm_model_specs
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.utils.model_downloader import download_models


class OutputFormat(str, Enum):
    """Supported output formats"""

    JSON = "json"
    MARKDOWN = "markdown"
    DOCTAGS = "doctags"
    TEXT = "text"


class PipelineType(str, Enum):
    """Pipeline types"""

    STANDARD = "standard"
    VLM = "vlm"


class VlmModel(str, Enum):
    """Predefined VLM models"""

    SMOL_DOCLING = "smol_docling"
    SMOL_DOCLING_MLX = "smol_docling_mlx"
    GRANITE_DOCLING = "granite_docling"
    GRANITE_DOCLING_MLX = "granite_docling_mlx"
    GRANITE_VISION = "granite_vision"
    CUSTOM = "custom"


class ParserConfig(BaseModel):
    """Configuration for PDF parser"""

    # Pipeline Type
    pipeline_type: PipelineType = Field(
        default=PipelineType.STANDARD, description="Pipeline type to use"
    )

    # OCR Settings
    enable_ocr: bool = Field(default=True, description="Enable OCR for scanned content")
    ocr_languages: List[str] = Field(default=["en"], description="OCR languages")

    # Table Processing
    enable_table_structure: bool = Field(
        default=True, description="Enable table structure recognition"
    )
    match_table_cells: bool = Field(
        default=True, description="Match table structure to PDF cells"
    )

    # Performance
    num_threads: int = Field(
        default=4, ge=1, le=16, description="Number of processing threads"
    )
    use_gpu: bool = Field(default=True, description="Use GPU acceleration if available")

    # Model Management
    artifacts_path: Optional[str] = Field(
        default=None, description="Path to prefetched models for offline usage"
    )
    auto_download_models: bool = Field(
        default=False,
        description="Automatically download models if artifacts_path is set",
    )

    # VLM Options
    vlm_model: VlmModel = Field(
        default=VlmModel.SMOL_DOCLING, description="VLM model to use"
    )
    vlm_custom_repo_id: Optional[str] = Field(
        default=None, description="Custom HuggingFace repo ID for VLM"
    )
    vlm_prompt: str = Field(
        default="Convert this page to docling.", description="VLM prompt"
    )
    vlm_response_format: ResponseFormat = Field(
        default=ResponseFormat.DOCTAGS, description="VLM response format"
    )
    vlm_inference_framework: InferenceFramework = Field(
        default=InferenceFramework.TRANSFORMERS, description="VLM inference framework"
    )

    # Picture Description (for standard pipeline)
    enable_picture_description: bool = Field(
        default=False, description="Enable picture description in standard pipeline"
    )
    picture_description_prompt: str = Field(
        default="Describe the image in three sentences. Be concise and accurate.",
        description="Picture description prompt",
    )

    # Remote Services
    enable_remote_services: bool = Field(
        default=False, description="Enable remote VLM services"
    )
    api_url: Optional[str] = Field(default=None, description="API URL for remote VLM")
    api_model: Optional[str] = Field(default=None, description="API model name")

    # Advanced VLM Options
    force_backend_text: bool = Field(
        default=False, description="Use backend text instead of VLM-generated text"
    )
    generate_page_images: bool = Field(
        default=True, description="Generate page images for VLM processing"
    )


class ParseResult(BaseModel):
    """Result of PDF parsing operation"""

    success: bool
    file_path: str
    processing_time: float
    page_count: int

    # Content formats
    json_content: Optional[Dict[str, Any]] = None
    markdown_content: Optional[str] = None
    doctags_content: Optional[str] = None
    text_content: Optional[str] = None

    # Metadata
    title: Optional[str] = None
    error_message: Optional[str] = None


class PDFDocumentParser:
    """PDF document parser using Docling with VLM support"""

    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize parser with configuration"""
        self.config = config or ParserConfig()

        # Handle model prefetching if requested
        if self.config.artifacts_path and self.config.auto_download_models:
            self.download_models()

        self._converter = self._create_converter()

    def download_models(self, target_path: Optional[str] = None) -> None:
        """Download models for offline usage"""
        download_path = target_path or self.config.artifacts_path

        if download_path:
            logger.info(f"Downloading models to: {download_path}")
            try:
                download_models(download_path)
                logger.info("Models downloaded successfully")
                # Update config with the download path
                if target_path:
                    self.config.artifacts_path = target_path
            except Exception as e:
                logger.error(f"Failed to download models: {e}")
                raise
        else:
            logger.info("Downloading models to default cache location")
            download_models()
            logger.info("Models downloaded to default cache")

    def _get_vlm_options(self) -> Union[HuggingFaceVlmOptions, ApiVlmOptions]:
        """Get VLM options based on configuration"""
        if self.config.enable_remote_services and self.config.api_url:
            # Use API-based VLM
            return ApiVlmOptions(
                url=self.config.api_url,
                params={"model": self.config.api_model}
                if self.config.api_model
                else {},
                prompt=self.config.vlm_prompt,
                response_format=self.config.vlm_response_format,
                timeout=120,
            )

        # Use local VLM
        if self.config.vlm_model == VlmModel.CUSTOM and self.config.vlm_custom_repo_id:
            repo_id = self.config.vlm_custom_repo_id
        else:
            # Map predefined models
            model_map = {
                VlmModel.SMOL_DOCLING: vlm_model_specs.SMOLDOCLING_TRANSFORMERS,
                VlmModel.SMOL_DOCLING_MLX: vlm_model_specs.SMOLDOCLING_MLX,
                VlmModel.GRANITE_DOCLING: vlm_model_specs.GRANITEDOCLING_TRANSFORMERS,
                VlmModel.GRANITE_DOCLING_MLX: vlm_model_specs.GRANITEDOCLING_MLX,
                VlmModel.GRANITE_VISION: vlm_model_specs.GRANITEV3_TRANSFORMERS,
            }
            return model_map.get(
                self.config.vlm_model, vlm_model_specs.SMOLDOCLING_TRANSFORMERS
            )

        return HuggingFaceVlmOptions(
            repo_id=repo_id,
            prompt=self.config.vlm_prompt,
            response_format=self.config.vlm_response_format,
            inference_framework=self.config.vlm_inference_framework,
        )

    def _create_converter(self) -> DocumentConverter:
        """Create DocumentConverter with optimized settings"""
        if self.config.pipeline_type == PipelineType.VLM:
            return self._create_vlm_converter()
        else:
            return self._create_standard_converter()

    def _create_vlm_converter(self) -> DocumentConverter:
        """Create VLM pipeline converter"""
        pipeline_options = VlmPipelineOptions()

        # Set artifacts path for prefetched models
        if self.config.artifacts_path:
            pipeline_options.artifacts_path = self.config.artifacts_path
            logger.info(f"Using prefetched models from: {self.config.artifacts_path}")

        # VLM-specific options
        pipeline_options.vlm_options = self._get_vlm_options()
        pipeline_options.force_backend_text = self.config.force_backend_text
        pipeline_options.generate_page_images = self.config.generate_page_images

        # Remote services
        if self.config.enable_remote_services:
            pipeline_options.enable_remote_services = True

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=VlmPipeline, pipeline_options=pipeline_options
                )
            }
        )

    def _create_standard_converter(self) -> DocumentConverter:
        """Create standard pipeline converter"""
        pipeline_options = PdfPipelineOptions()

        # Set artifacts path for prefetched models
        if self.config.artifacts_path:
            pipeline_options.artifacts_path = self.config.artifacts_path
            logger.info(f"Using prefetched models from: {self.config.artifacts_path}")

        # OCR settings
        pipeline_options.do_ocr = self.config.enable_ocr
        if self.config.enable_ocr:
            pipeline_options.ocr_options.lang = self.config.ocr_languages

        # Table processing
        pipeline_options.do_table_structure = self.config.enable_table_structure
        pipeline_options.table_structure_options.do_cell_matching = (
            self.config.match_table_cells
        )

        # Picture description
        if self.config.enable_picture_description:
            pipeline_options.do_picture_description = True
            pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
                prompt=self.config.picture_description_prompt
            )

        # Performance settings
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=self.config.num_threads,
            device=AcceleratorDevice.AUTO
            if self.config.use_gpu
            else AcceleratorDevice.CPU,
        )

        # Image generation
        pipeline_options.generate_page_images = self.config.generate_page_images

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse_document(
        self,
        file_path: Union[str, Path],
        output_formats: Optional[List[OutputFormat]] = None,
    ) -> ParseResult:
        """Parse a PDF document and return results in requested formats"""
        if output_formats is None:
            output_formats = list(OutputFormat)

        file_path = str(file_path)
        start_time = time.time()

        try:
            logger.info(f"Starting to parse document: {file_path}")

            # Convert document
            conv_result = self._converter.convert(file_path)
            processing_time = time.time() - start_time

            # Extract basic metadata
            document = conv_result.document
            page_count = len(document.pages) if hasattr(document, "pages") else 0

            # Initialize result
            result = ParseResult(
                success=True,
                file_path=file_path,
                processing_time=processing_time,
                page_count=page_count,
            )

            # Generate output formats
            if OutputFormat.JSON in output_formats:
                result.json_content = document.export_to_dict()

            if OutputFormat.MARKDOWN in output_formats:
                result.markdown_content = document.export_to_markdown()

            if OutputFormat.DOCTAGS in output_formats:
                result.doctags_content = document.export_to_document_tokens()

            if OutputFormat.TEXT in output_formats:
                result.text_content = document.export_to_text()

            # Extract title from JSON (if available)
            if result.json_content and "main_text" in result.json_content:
                main_text = result.json_content.get("main_text", [])
                for item in main_text[:3]:
                    if item.get("label") == "title":
                        result.title = item.get("text", "").strip()
                        break

            logger.info(
                f"Successfully parsed document in {processing_time:.2f}s. Pages: {page_count}"
            )
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to parse document: {str(e)}"
            logger.error(error_msg)

            return ParseResult(
                success=False,
                file_path=file_path,
                processing_time=processing_time,
                page_count=0,
                error_message=error_msg,
            )


def create_parser(
    enable_ocr: bool = True,
    languages: Optional[List[str]] = None,
    use_gpu: bool = True,
    num_threads: int = 4,
    artifacts_path: Optional[str] = None,
    auto_download_models: bool = False,
    pipeline_type: PipelineType = PipelineType.STANDARD,
    vlm_model: VlmModel = VlmModel.SMOL_DOCLING,
    enable_picture_description: bool = False,
) -> PDFDocumentParser:
    """Convenience function to create parser with common settings"""
    config = ParserConfig(
        enable_ocr=enable_ocr,
        ocr_languages=languages or ["en"],
        use_gpu=use_gpu,
        num_threads=num_threads,
        artifacts_path=artifacts_path,
        auto_download_models=auto_download_models,
        pipeline_type=pipeline_type,
        vlm_model=vlm_model,
        enable_picture_description=enable_picture_description,
    )
    return PDFDocumentParser(config)


def create_vlm_parser(
    vlm_model: VlmModel = VlmModel.SMOL_DOCLING,
    vlm_prompt: str = "Convert this page to docling.",
    response_format: ResponseFormat = ResponseFormat.DOCTAGS,
    artifacts_path: Optional[str] = None,
    use_gpu: bool = True,
) -> PDFDocumentParser:
    """Convenience function to create VLM parser"""
    config = ParserConfig(
        pipeline_type=PipelineType.VLM,
        vlm_model=vlm_model,
        vlm_prompt=vlm_prompt,
        vlm_response_format=response_format,
        artifacts_path=artifacts_path,
        use_gpu=use_gpu,
        generate_page_images=True,  # Required for VLM
    )
    return PDFDocumentParser(config)


def save_results_to_files(
    result: ParseResult, output_dir: Union[str, Path] = "output"
) -> None:
    """Save parsing results to files"""
    import json

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    base_name = Path(result.file_path).stem

    if result.markdown_content:
        with open(output_path / f"{base_name}.md", "w", encoding="utf-8") as f:
            f.write(result.markdown_content)
        logger.info(f"Saved markdown: {output_path / f'{base_name}.md'}")

    if result.json_content:
        with open(output_path / f"{base_name}.json", "w", encoding="utf-8") as f:
            json.dump(result.json_content, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON: {output_path / f'{base_name}.json'}")

    if result.doctags_content:
        with open(output_path / f"{base_name}.doctags", "w", encoding="utf-8") as f:
            f.write(result.doctags_content)
        logger.info(f"Saved DocTags: {output_path / f'{base_name}.doctags'}")

    if result.text_content:
        with open(output_path / f"{base_name}.txt", "w", encoding="utf-8") as f:
            f.write(result.text_content)
        logger.info(f"Saved text: {output_path / f'{base_name}.txt'}")


if __name__ == "__main__":
    # Example 1: Standard pipeline (traditional OCR + table recognition)
    print("=== Standard Pipeline ===")
    parser = create_parser()

    # Example 2: Standard pipeline with picture descriptions
    # parser = create_parser(enable_picture_description=True)

    # Example 3: VLM Pipeline - SmolDocling for full page processing
    # print("=== VLM Pipeline (SmolDocling) ===")
    # parser = create_vlm_parser(vlm_model=VlmModel.SMOL_DOCLING)

    # Example 4: VLM Pipeline - Granite Vision for markdown output
    # print("=== VLM Pipeline (Granite Vision) ===")
    # parser = create_vlm_parser(
    #     vlm_model=VlmModel.GRANITE_VISION,
    #     vlm_prompt="OCR this page to markdown.",
    #     response_format=ResponseFormat.MARKDOWN
    # )

    # Example 5: Custom VLM model
    # config = ParserConfig(
    #     pipeline_type=PipelineType.VLM,
    #     vlm_model=VlmModel.CUSTOM,
    #     vlm_custom_repo_id="your-custom/vlm-model",
    #     vlm_prompt="Convert this document page.",
    #     vlm_response_format=ResponseFormat.DOCTAGS
    # )
    # parser = PDFDocumentParser(config)

    # Example 6: Remote API VLM (e.g., Ollama, LM Studio)
    # config = ParserConfig(
    #     pipeline_type=PipelineType.VLM,
    #     enable_remote_services=True,
    #     api_url="http://localhost:11434/v1/chat/completions",
    #     api_model="granite3.2-vision:latest",
    #     vlm_prompt="OCR this page to markdown.",
    #     vlm_response_format=ResponseFormat.MARKDOWN
    # )
    # parser = PDFDocumentParser(config)

    # Test with your PDF
    pdf_path = "data/pdf/first_few_pages.pdf"
    result = parser.parse_document(
        pdf_path, output_formats=[OutputFormat.MARKDOWN, OutputFormat.JSON]
    )

    if result.success:
        print(f"✅ Parsed successfully in {result.processing_time:.2f}s")
        print(f"📄 Pages: {result.page_count}")
        print(f"🔧 Pipeline: {parser.config.pipeline_type.value}")
        if result.title:
            print(f"📝 Title: {result.title}")

        save_results_to_files(result)

        # Show preview
        if result.markdown_content:
            print("\n📝 Markdown Preview (first 500 chars):")
            print("-" * 50)
            preview = result.markdown_content[:500]
            print(preview + "..." if len(result.markdown_content) > 500 else preview)
            print("-" * 50)
    else:
        print(f"❌ Failed: {result.error_message}")

    # Test with arXiv URL using VLM
    print("\n" + "=" * 60)
    print("Testing VLM pipeline with arXiv document...")

    vlm_parser = create_vlm_parser(
        vlm_model=VlmModel.SMOL_DOCLING, response_format=ResponseFormat.MARKDOWN
    )

    url_result = vlm_parser.parse_document(
        "https://arxiv.org/pdf/2408.09869", output_formats=[OutputFormat.MARKDOWN]
    )

    if url_result.success:
        print("✅ VLM document parsed successfully!")
        print(f"📄 Pages: {url_result.page_count}")
        print(f"🔧 Pipeline: VLM ({vlm_parser.config.vlm_model.value})")
        save_results_to_files(url_result, "arxiv_vlm_output")
    else:
        print(f"❌ VLM parsing failed: {url_result.error_message}")

    # Example: Manual model download for VLM models
    # parser.download_models("./vlm_models")
