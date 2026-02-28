"""LlamaCloud OCR service for PDF text extraction."""

from __future__ import annotations

from pathlib import Path

import aiofiles
import aiofiles.tempfile
import httpx
import logfire
from llama_cloud import AsyncLlamaCloud

from app.core.config import settings


@logfire.instrument("extract_text_from_pdf")
async def extract_text_from_pdf(
    source_url: str,
    page_separator: str = "\n\f\n",
) -> str:
    """Extract text from a PDF URL using LlamaCloud OCR.

    Downloads the PDF, uploads to LlamaCloud, and returns parsed markdown.

    Args:
        source_url: URL of the PDF file to process
        page_separator: Separator between pages in output

    Returns:
        Markdown text extracted from the PDF
    """
    async with (
        AsyncLlamaCloud(
            api_key=settings.LLAMA_CLOUD_API_KEY,
        ) as parser_client,
        httpx.AsyncClient(timeout=300) as http_client,
        aiofiles.tempfile.TemporaryDirectory() as temp_dir,  # pyright: ignore[reportUnknownMemberType]
    ):
        output_file_path = Path(temp_dir) / "temp.pdf"
        async with aiofiles.open(output_file_path, "wb") as temp_file:  # pyright: ignore[reportUnknownVariableType]
            response: httpx.Response = await http_client.get(source_url)
            response.raise_for_status()
            await temp_file.write(response.content)

        file_object = await parser_client.files.create(
            file=output_file_path,
            purpose="parse",
        )

        result = await parser_client.parsing.parse(
            file_id=file_object.id,
            tier="agentic",
            version="latest",
            expand=["markdown"],
            input_options={},
            output_options={
                "markdown": {
                    "annotate_links": True,
                    "tables": {
                        "output_tables_as_markdown": False,
                        "merge_continued_tables": True,
                    },
                },
                "extract_printed_page_number": True,
            },
            processing_options={
                "ignore": {
                    "ignore_diagonal_text": True,
                    "ignore_hidden_text": True,
                },
                "cost_optimizer": {
                    "enable": True,
                },
            },
        )

        if result.markdown is None:
            raise ValueError("No markdown found in the result")

        pages: list[str] = []
        for page in result.markdown.pages:
            markdown = page.markdown  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
            if not isinstance(markdown, str):
                continue
            pages.append(markdown)

        return page_separator.join(pages)


@logfire.instrument("extract_text_from_file")
async def extract_text_from_file(
    file_content: bytes,
    page_separator: str = "\n\f\n",
) -> str:
    """Extract text from PDF file bytes using LlamaCloud OCR.

    Args:
        file_content: Raw PDF file bytes
        page_separator: Separator between pages in output

    Returns:
        Markdown text extracted from the PDF
    """
    async with (
        AsyncLlamaCloud(
            api_key=settings.LLAMA_CLOUD_API_KEY,
        ) as parser_client,
        aiofiles.tempfile.TemporaryDirectory() as temp_dir,  # pyright: ignore[reportUnknownMemberType]
    ):
        output_file_path = Path(temp_dir) / "temp.pdf"
        async with aiofiles.open(output_file_path, "wb") as temp_file:  # pyright: ignore[reportUnknownVariableType]
            await temp_file.write(file_content)

        file_object = await parser_client.files.create(
            file=output_file_path,
            purpose="parse",
        )

        result = await parser_client.parsing.parse(
            file_id=file_object.id,
            tier="agentic",
            version="latest",
            expand=["markdown"],
            input_options={},
            output_options={
                "markdown": {
                    "annotate_links": True,
                    "tables": {
                        "output_tables_as_markdown": False,
                        "merge_continued_tables": True,
                    },
                },
                "extract_printed_page_number": True,
            },
            processing_options={
                "ignore": {
                    "ignore_diagonal_text": True,
                    "ignore_hidden_text": True,
                },
                "cost_optimizer": {
                    "enable": True,
                },
            },
        )

        if result.markdown is None:
            raise ValueError("No markdown found in the result")

        pages: list[str] = []
        for page in result.markdown.pages:
            markdown = page.markdown  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
            if not isinstance(markdown, str):
                continue
            pages.append(markdown)

        return page_separator.join(pages)
