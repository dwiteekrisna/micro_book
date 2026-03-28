import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageEnhance
import os

def render_page_as_image(pdf_path, page_number, zoom=3, enhance_contrast=True):
    """Render a PDF page as a darkened image (to make light text print-friendly)."""
    doc = fitz.open(pdf_path)
    if page_number >= len(doc):
        blank_doc = fitz.open()
        blank_doc.new_page(width=595, height=842)  # A4 size in points
        pix = blank_doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                      alpha=False)
    else:
        page = doc.load_page(page_number)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

    img_bytes = pix.tobytes("png")
    image = Image.open(BytesIO(img_bytes)).convert("RGB")

    # Enhance contrast to make text darker
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)  # Increase this value if needed

    enhanced_bytes = BytesIO()
    image.save(enhanced_bytes, format='PNG')
    enhanced_bytes.seek(0)
    return enhanced_bytes


def create_8up_pdf(input_pdf):
    doc = fitz.open(input_pdf)
    total_pages = len(doc)

    # Pad to multiple of 16
    pad_needed = (16 - (total_pages % 16)) % 16
    padded_total = total_pages + pad_needed

    # Page reordering logic (do not modify)
    reordered = []
    for i in range(0, padded_total, 16):
        reordered.extend(
            [i + 0, i + 2, i + 4, i + 6, i + 8, i + 10, i + 12,
             i + 14])  # Front
        reordered.extend(
            [i + 7, i + 5, i + 3, i + 1, i + 15, i + 13, i + 11,
             i + 9])  # Back

    # A4 landscape layout
    pw, ph = landscape(A4)
    col_w = pw / 4
    row_h = ph / 2

    # Position coordinates for 8 thumbnails (4 top, 4 bottom)
    positions = []
    for row in [1, 0]:  # Top row first
        for col in range(4):
            x = col * col_w
            y = row * row_h
            positions.append((x, y))

    pages = []
    for i in range(0, len(reordered), 8):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        for j in range(8):
            page_index = reordered[i + j]
            image_stream = render_page_as_image(input_pdf, page_index, zoom=3)
            image = ImageReader(image_stream)
            x, y = positions[j]
            c.drawImage(image, x, y, width=col_w, height=row_h)

            # Add page number below or above thumbnail
            c.setFont("Helvetica", 6)
            page_number_text = f"{page_index + 1}"
            text_y = y + (6 if j < 4 else 12)
            c.drawCentredString(x + col_w / 2, text_y, page_number_text)

        # Draw cutting lines
        c.setDash(2, 2)
        c.setLineWidth(0.5)
        c.setStrokeGray(0.5)
        c.line(0, ph / 2, pw, ph / 2)
        for k in range(1, 4):
            x = col_w * k
            c.line(x, 0, x, ph)

        c.showPage()
        c.save()
        buffer.seek(0)
        pages.append(fitz.open("pdf", buffer.read()))

    # Combine all pages into a final PDF
    final_doc = fitz.open()
    for part in pages:
        final_doc.insert_pdf(part)

    # Save with dynamic name
    base_name = os.path.splitext(os.path.basename(input_pdf))[0]
    output_pdf = f"micro_{base_name}.pdf"
    final_doc.save(output_pdf)
    print(f"✅ Created PDF: {output_pdf}")


# Example usage
create_8up_pdf(input('Enter The file name : '))
