import datetime
from flask import Flask, render_template, request, Response
import os
from PyPDF4 import PdfFileReader, PdfFileWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import math
from reportlab.lib.colors import lightgrey
import socket
import webbrowser  # Import the webbrowser module

app = Flask(__name__)

# Define a default upload folder or use the 'uploads' folder in the current directory as a fallback.
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/watermark', methods=['POST'])
def watermark():
    upload_folder = app.config['UPLOAD_FOLDER']

    if 'pdf_files[]' not in request.files:
        return "No PDF files provided."

    pdf_files = request.files.getlist('pdf_files[]')
    if len(pdf_files) == 0:
        return "No selected files."

    watermark_text = request.form['watermark_text']
    opacity = float(request.form['opacity'])

    # Apply watermark and footer to each PDF file
    watermarked_pdfs = []
    for pdf_file in pdf_files:
        watermarked_pdf = watermark_pdf(pdf_file, watermark_text, opacity)
        watermarked_pdfs.append(watermarked_pdf)
    
    # Combine watermarked PDFs into a single PDF
    combined_pdf = combine_pdfs(watermarked_pdfs)

    # Return the combined watermarked PDF as a response with content type set to PDF
    return Response(combined_pdf, content_type='application/pdf')

def create_watermark_canvas(text, page_width, page_height, opacity):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    c.setFillColor(lightgrey)
    c.setFont("Helvetica", 16)

    # Calculate the optimal number of columns based on text length
    max_string_width = max([float(c.stringWidth(line, "Helvetica", 16)) for line in text.split('\n')])
    num_columns = min(3, int(float(page_width) / max_string_width))  # Maximum 3 columns

    # Calculate the column spacing
    column_spacing = float(page_width) / num_columns

    for column in range(num_columns):
        # Calculate the x-coordinate for each column
        x = column * column_spacing

        # Calculate the y-coordinate to start at the top and move down
        y = float(page_height)

        lines = text.split('\n')
        line_height = 16  # Initial line height
        for line in lines:
            # Calculate the string width and adjust line height if needed
            string_width = float(c.stringWidth(line, "Helvetica", 16))
            if string_width > column_spacing:
                line_height = 10  # Reduce line height for long text

            while y > 0:
                c.saveState()
                c.translate(float(x), float(y))  # Cast to float to avoid the TypeError
                c.setFillAlpha(opacity)  # Set the opacity
                c.drawString(0, 0, line)
                c.restoreState()
                y -= line_height  # Adjust the vertical spacing based on line height

    c.save()
    packet.seek(0)

    return packet

def create_footer_canvas(text, page_width, page_height):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    c.setFont("Helvetica", 7)

    # Calculate the x-coordinate to center the text horizontally
    string_width = c.stringWidth(text, "Helvetica", 7)
    footer_x = (float(page_width) - float(string_width)) / 2  # Explicitly convert to float
    footer_y = 20  # Adjust the vertical position as needed

    c.drawString(footer_x, footer_y, text)

    c.save()
    packet.seek(0)
    return packet

def watermark_pdf(pdf_file, text, opacity):
    pdf_reader = PdfFileReader(pdf_file)
    pdf_writer = PdfFileWriter()

    for page_num in range(pdf_reader.getNumPages()):
        # Create a watermark canvas for the current page
        page = pdf_reader.getPage(page_num)
        page_width = page.mediaBox.getWidth()
        page_height = page.mediaBox.getHeight()
        watermark_canvas = create_watermark_canvas(text, page_width, page_height, opacity)

        # Merge the watermark canvas with the current page
        watermark_pdf = PdfFileReader(watermark_canvas)
        watermark_page = watermark_pdf.getPage(0)
        page.mergePage(watermark_page)

        #Apply current date and time
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
        # Create a footer canvas for the current page
        footer_canvas = create_footer_canvas(f" {socket.gethostname()} | {current_datetime}", page_width, page_height)

        # Merge the footer canvas with the current page
        footer_pdf = PdfFileReader(footer_canvas)
        footer_page = footer_pdf.getPage(0)
        page.mergeTranslatedPage(footer_page, 0, 0)

        pdf_writer.addPage(page)

    output_pdf = BytesIO()
    pdf_writer.write(output_pdf)
    output_pdf.seek(0)

    return output_pdf.getvalue()

def combine_pdfs(pdf_list):
    pdf_writer = PdfFileWriter()
    for pdf_data in pdf_list:
        pdf_reader = PdfFileReader(BytesIO(pdf_data))
        for page_num in range(pdf_reader.getNumPages()):
            page = pdf_reader.getPage(page_num)
            pdf_writer.addPage(page)

    combined_pdf = BytesIO()
    pdf_writer.write(combined_pdf)
    combined_pdf.seek(0)

    return combined_pdf.getvalue()

if __name__ == '__main__':
    # Ensure the specified or default upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Open the web browser automatically
    webbrowser.open('http://127.0.0.1:5000/')
    
    # Run the Flask app
    app.run(debug=True)
