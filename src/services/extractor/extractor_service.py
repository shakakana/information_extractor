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
    AcceleratorOptions,
    AcceleratorDevice,
)


class OutputFormat(str, Enum):
    """Supported output formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    DOCTAGS = "doctags"
    TEXT = "text"


class ParserConfig(BaseModel):
    """Configuration for PDF parser"""
    
    # OCR Settings
    enable_ocr: bool = Field(default=True, description="Enable OCR for scanned content")
    ocr_languages: List[str] = Field(default=["en"], description="OCR languages")
    
    # Table Processing
    enable_table_structure: bool = Field(default=True, description="Enable table structure recognition")
    match_table_cells: bool = Field(default=True, description="Match table structure to PDF cells")
    
    # Performance
    num_threads: int = Field(default=4, ge=1, le=16, description="Number of processing threads")
    use_gpu: bool = Field(default=True, description="Use GPU acceleration if available")


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
    """PDF document parser using Docling"""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize parser with configuration"""
        self.config = config or ParserConfig()
        self._converter = self._create_converter()
        
    def _create_converter(self) -> DocumentConverter:
        """Create DocumentConverter with optimized settings"""
        pipeline_options = PdfPipelineOptions()
        
        # OCR settings
        pipeline_options.do_ocr = self.config.enable_ocr
        if self.config.enable_ocr:
            pipeline_options.ocr_options.lang = self.config.ocr_languages
        
        # Table processing
        pipeline_options.do_table_structure = self.config.enable_table_structure
        pipeline_options.table_structure_options.do_cell_matching = self.config.match_table_cells
        
        # Performance settings
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=self.config.num_threads,
            device=AcceleratorDevice.AUTO if self.config.use_gpu else AcceleratorDevice.CPU
        )
        
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    
    def parse_document(
        self, 
        file_path: Union[str, Path], 
        output_formats: Optional[List[OutputFormat]] = None
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
            page_count = len(document.pages) if hasattr(document, 'pages') else 0
            
            # Initialize result
            result = ParseResult(
                success=True,
                file_path=file_path,
                processing_time=processing_time,
                page_count=page_count
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
            if result.json_content and 'main_text' in result.json_content:
                main_text = result.json_content.get('main_text', [])
                for item in main_text[:3]:
                    if item.get('label') == 'title':
                        result.title = item.get('text', '').strip()
                        break
            
            logger.info(f"Successfully parsed document in {processing_time:.2f}s. Pages: {page_count}")
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
                error_message=error_msg
            )


def create_parser(
    enable_ocr: bool = True,
    languages: Optional[List[str]] = None,
    use_gpu: bool = True,
    num_threads: int = 4
) -> PDFDocumentParser:
    """Convenience function to create parser with common settings"""
    config = ParserConfig(
        enable_ocr=enable_ocr,
        ocr_languages=languages or ["en"],
        use_gpu=use_gpu,
        num_threads=num_threads
    )
    return PDFDocumentParser(config)


def save_results_to_files(result: ParseResult, output_dir: Union[str, Path] = "output") -> None:
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
    parser = create_parser()
    
    # Test with your PDF
    pdf_path = "data/pdf/first_few_pages.pdf"
    result = parser.parse_document(
        pdf_path,
        output_formats=[OutputFormat.MARKDOWN, OutputFormat.JSON]
    )
    
    if result.success:
        print(f"✅ Parsed successfully in {result.processing_time:.2f}s")
        print(f"📄 Pages: {result.page_count}")
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
    
    # Test with arXiv URL
    print("\n" + "="*60)
    print("Testing with arXiv document...")
    
    url_result = parser.parse_document(
        "https://arxiv.org/pdf/2408.09869",
        output_formats=[OutputFormat.MARKDOWN]
    )
    
    if url_result.success:
        print(f"✅ URL document parsed successfully!")
        print(f"📄 Pages: {url_result.page_count}")
        save_results_to_files(url_result, "arxiv_output")
    else:
        print(f"❌ URL parsing failed: {url_result.error_message}")