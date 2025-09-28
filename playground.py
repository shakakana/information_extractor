from pathlib import Path
from typing import Optional, Union, List
from loguru import logger
from src.services.extractor.extractor_service import (
    PDFDocumentParser,
    ParserConfig,
    ParseResult,
    OutputFormat,
    PipelineType,
    VlmModel,
    ResponseFormat,
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
    # print("=== Standard Pipeline ===")
    logger.info("=== Standard Pipeline ===")
    parser = create_parser()

    # Example 2: Standard pipeline with picture descriptions
    # parser = create_parser(enable_picture_description=True)

    # Example 3: VLM Pipeline - SmolDocling for full page processing
    ## print("=== VLM Pipeline (SmolDocling) ===")
    # logger.info("=== VLM Pipeline (SmolDocling) ===")
    # parser = create_vlm_parser(vlm_model=VlmModel.SMOL_DOCLING)

    # Example 4: VLM Pipeline - Granite Vision for markdown output
    ## print("=== VLM Pipeline (Granite Vision) ===")
    # logger.info("=== VLM Pipeline (Granite Vision) ===")
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
    pdf_path = "data/first_few_pages.pdf"
    result = parser.parse_document(
        pdf_path, output_formats=[OutputFormat.MARKDOWN, OutputFormat.JSON]
    )

    if result.success:
        # print(f"✅ Parsed successfully in {result.processing_time:.2f}s")
        # print(f"📄 Pages: {result.page_count}")
        # print(f"🔧 Pipeline: {parser.config.pipeline_type.value}")
        logger.info(f"✅ Parsed successfully in {result.processing_time:.2f}s")
        logger.info(f"📄 Pages: {result.page_count}")
        logger.info(f"🔧 Pipeline: {parser.config.pipeline_type.value}")
        if result.title:
            # print(f"📝 Title: {result.title}")
            logger.info(f"📝 Title: {result.title}")

        save_results_to_files(result)

        # Show preview
        if result.markdown_content:
            # print("\n📝 Markdown Preview (first 500 chars):")
            # print("-" * 50)
            logger.info("\n📝 Markdown Preview (first 500 chars):")
            logger.info("-" * 50)
            preview = result.markdown_content[:500]
            # print(preview + "..." if len(result.markdown_content) > 500 else preview)
            # print("-" * 50)
            logger.info(
                preview + "..." if len(result.markdown_content) > 500 else preview
            )
            logger.info("-" * 50)
    else:
        # print(f"❌ Failed: {result.error_message}")
        logger.error(f"❌ Failed: {result.error_message}")

    # Test with arXiv URL using VLM
    # print("\n" + "=" * 60)
    # print("Testing VLM pipeline with arXiv document...")
    logger.info("\n" + "=" * 60)
    logger.info("Testing VLM pipeline with arXiv document...")

    vlm_parser = create_vlm_parser(
        vlm_model=VlmModel.SMOL_DOCLING, response_format=ResponseFormat.MARKDOWN
    )

    url_result = vlm_parser.parse_document(
        "https://arxiv.org/pdf/2408.09869", output_formats=[OutputFormat.MARKDOWN]
    )

    if url_result.success:
        # print("✅ VLM document parsed successfully!")
        # print(f"📄 Pages: {url_result.page_count}")
        # print(f"🔧 Pipeline: VLM ({vlm_parser.config.vlm_model.value})")
        logger.info("✅ VLM document parsed successfully!")
        logger.info(f"📄 Pages: {url_result.page_count}")
        logger.info(f"🔧 Pipeline: VLM ({vlm_parser.config.vlm_model.value})")
        save_results_to_files(url_result, "arxiv_vlm_output")
    else:
        # print(f"❌ VLM parsing failed: {url_result.error_message}")
        logger.error(f"❌ VLM parsing failed: {url_result.error_message}")

    # Example: Manual model download for VLM models
    # parser.download_models("./vlm_models")
