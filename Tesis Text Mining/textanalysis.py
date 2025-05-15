import pdfplumber

def extract_ordered_text(pdf_path, page_num):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num] 
        words = page.extract_words() 

        return words

pdf_path = "periodico.pdf"
page_num = 25

text = extract_ordered_text(pdf_path, page_num)
print(text)

