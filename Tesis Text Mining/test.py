import pandas as pd
import numpy as np
import nltk
import re
from pypdf import PdfReader
nltk.download('punkt')
nltk.download('punkt_tab') 
nltk.download('stopwords')  
nltk.download('wordnet')  

reader = PdfReader("periodico.pdf")

#extraer todas las páginas
#for each in range(len(reader.pages)):
#    page = reader.pages[each]
#    print(page.extract_text())


text = reader.pages[26].extract_text()
text = re.sub(r'\s+', ' ', text)
print(text)

date_pattern = r"\b\d{4}\b"

from nltk.tokenize import word_tokenize
token = word_tokenize(text)
#Limpieza
for t in token:
    t = t.strip()

print(token)

dpattern = re.compile(r"^\d{4}$")
anpattern = re.compile(r"^\d{4}[A-Za-z]+$")  

extracted_texts = []
current_extraction = []

for i, t in enumerate(token):
   if dpattern.match(t):
      print(f"years: {t}")
      if i+2 < len(token) and anpattern.match(token[i + 3]):
        match = f"{token[i]} {token[i+1]} {token[i+3]}"
        print(f"Pattern match: {match}")
    

