from pdf2image import convert_from_path

# Path to your PDF file
pdf_path = "periodico.pdf"

# Explicitly set the path to Poppler's `bin` directory
poppler_path = r"C:\poppler-24.08.0\Library\bin"  # Replace with the correct path

# Convert PDF to images
try:
    images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)

    # Save the images
    for i, image in enumerate(images):
        image.save(f"page_{i + 1}.jpg", "JPEG")
    print("PDF successfully converted to images!")

except Exception as e:
    print(f"An error occurred: {e}")