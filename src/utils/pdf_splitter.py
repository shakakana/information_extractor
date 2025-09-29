"""
Simple PDF page splitter utility
Splits a PDF into separate files based on page ranges
"""

import os
import sys
from pypdf import PdfReader, PdfWriter


def split_pdf(input_path, output_dir, page_ranges):
    """
    Split PDF into multiple files based on page ranges.

    Args:
        input_path: Path to input PDF file
        output_dir: Directory to save output files
        page_ranges: List of tuples (start, end) for page ranges (1-indexed)
                    e.g., [(1, 3), (4, 5), (6, 10)]
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Read the input PDF
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)

    print(f"Input PDF has {total_pages} pages")

    # Process each page range
    for i, (start, end) in enumerate(page_ranges, 1):
        # Convert to 0-indexed
        start_idx = start - 1
        end_idx = end

        # Validate page range
        if start_idx < 0 or end_idx > total_pages:
            print(f"Warning: Range {start}-{end} is out of bounds. Skipping.")
            continue

        # Create a new PDF with the specified pages
        writer = PdfWriter()
        for page_num in range(start_idx, end_idx):
            writer.add_page(reader.pages[page_num])

        # Generate output filename
        output_filename = f"split_{i}_pages_{start}-{end}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        # Write the output file
        with open(output_path, "wb") as f:
            writer.write(f)

        print(f"Created: {output_filename} (pages {start}-{end})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_splitter.py <input.pdf>")
        print("\nExample:")
        print("  python pdf_splitter.py document.pdf")
        print("\nThen follow the prompts to specify page ranges.")
        sys.exit(1)

    input_pdf = sys.argv[1]

    if not os.path.exists(input_pdf):
        print(f"Error: File '{input_pdf}' not found")
        sys.exit(1)

    # Get output directory
    output_dir = input("Output directory [default: output]: ").strip() or "output"

    # Get page ranges
    print("\nEnter page ranges to split (1-indexed):")
    print("Examples:")
    print("  1-3,4-5,6-10  (split into 3 files)")
    print("  1-1,2-2,3-5   (pages 1, 2, and 3-5)")

    ranges_input = input("Page ranges: ").strip()

    # Parse page ranges
    page_ranges = []
    for range_str in ranges_input.split(","):
        range_str = range_str.strip()
        if "-" in range_str:
            start, end = map(int, range_str.split("-"))
            page_ranges.append((start, end))
        else:
            page = int(range_str)
            page_ranges.append((page, page))

    # Split the PDF
    split_pdf(input_pdf, output_dir, page_ranges)
    print(f"\nDone! Files saved to '{output_dir}/'")


if __name__ == "__main__":
    main()
