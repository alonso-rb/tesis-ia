import pytesseract as tess
from PIL import Image
from transformers import LayoutLMv3Processor

# Set up Tesseract path (if necessary)
tess.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load the image
image = Image.open("page_26.jpg")

# Use Tesseract to extract OCR data with bounding boxes
ocr_data = tess.image_to_data(image, output_type=tess.Output.DICT, lang='spa')

# Extract words and their corresponding bounding boxes
words = []
bboxes = []
for i in range(len(ocr_data['text'])):
    if int(ocr_data['conf'][i]) > 0:  # Only consider words with a valid confidence level
        words.append(ocr_data['text'][i])
        # Extracting bounding box data (x1, y1, x2, y2)
        bboxes.append([ocr_data['left'][i], ocr_data['top'][i], 
                       ocr_data['left'][i] + ocr_data['width'][i], 
                       ocr_data['top'][i] + ocr_data['height'][i]])

# Initialize the LayoutLMv3 processor
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")

# Process the image, words, and bounding boxes
encoding = processor(image, words=words, boxes=bboxes, return_tensors="pt", truncation=True, padding=True)

# Now you can pass the encoded inputs to a model for further tasks
print(encoding)
