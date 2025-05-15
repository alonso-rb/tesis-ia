from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader('periodico.pdf')
pages = loader.load()
specific_page = pages[26]
print(specific_page)

import ollama
response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': """Reorganize the following text to ensure it has semantic coherence and flows logically. MANTAIN the original meaning DO NOT add or remove text, ONLY reorganize it. The text is in Spanish, so please preserve the original language."""
    }, {
        'role': 'user',
        'content': specific_page.page_content
    }]
)

print(response.message.content)

response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': """Separate the text into each news article, the output should be a JSON with each new containing Titular and content."""
    }, {
        'role': 'user',
        'content': response.message.content
    }]
)

print(response.message.content)
json_message = response.message.content

start_char = "["
end_char = "]"

#Get AI response
message = json_message

#Clean AI Response
start_index = message.find(start_char)
end_index = message.find(end_char)+1
json_message = message[start_index:end_index]
print(json_message)
