# Requires !pip install PyMuPDF, see: https://github.com/pymupdf/pymupdf
import fitz # (pymupdf, found this is better than pypdf for our use case, note: licence is AGPL-3.0, keep that in mind if you want to use any code commercially)
from tqdm.auto import tqdm # for progress bars, requires !pip install tqdm
import random
import spacy
from spacy.lang.ro import Romanian
import glob
import json

def text_formatter(text: str) -> str:
    """Performs minor formatting on text."""
    cleaned_text = text.replace("\n", " ").strip() # note: this might be different for each doc (best to experiment)
    #cleaned_text = text.replace("  "," ").strip();
    # Other potential text formatting functions can go here
    return cleaned_text

# Open PDF and get lines/pages
# Note: this only focuses on text, rather than images/figures etc
def open_and_read_pdf(pdf_path: str) -> list[dict]:
    """
    Opens a PDF file, reads its text content page by page, and collects statistics.

    Parameters:
        pdf_path (str): The file path to the PDF document to be opened and read.

    Returns:
        list[dict]: A list of dictionaries, each containing the page number
        (adjusted), character count, word count, sentence count, token count, and the extracted text
        for each page.
    """
    doc = fitz.open(pdf_path)  # open a document
    pages_and_texts = []
    for page_number, page in tqdm(enumerate(doc)):  # iterate the document pages
        text = page.get_text()  # get plain text encoded as UTF-8
        text = text_formatter(text)
        pages_and_texts.append({"page_number": page_number,  # adjust page numbers since our PDF starts on page 0
                                "page_char_count": len(text),
                                "page_word_count": len(text.split(" ")),
                                "page_sentence_count_raw": len(text.split(". ")),
                                "page_token_count": len(text) / 4,  # 1 token = ~4 chars, see: https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
                                "text": text})
    return pages_and_texts


#pages_and_texts = open_and_read_pdf(pdf_path="pdfs/teste-admitere-informatica-02.03.2020.pdf")
pdf_files = glob.glob("pdfs/Fizica/*.pdf")
all_pages_and_texts = []

nlp = Romanian()

# Add a sentencizer pipeline, see https://spacy.io/api/sentencizer/
nlp.add_pipe("sentencizer")

for pdf_file in pdf_files:
    pages_and_texts = open_and_read_pdf(pdf_file)

    # Process the extracted text with Spacy
    for item in tqdm(pages_and_texts, desc=f"Analyzing {pdf_file}"):
        item["sentences"] = list(nlp(item["text"]).sents)

        # Make sure all sentences are strings
        item["sentences"] = [str(sentence) for sentence in item["sentences"]]

        # Count the sentences
        item["page_sentence_count_spacy"] = len(item["sentences"])

    all_pages_and_texts.extend(pages_and_texts)


print(random.sample(all_pages_and_texts, k=1))

file_path = "teste_admitere_fizica.json"

# Write the list to the JSON file
with open(file_path, "w") as json_file:
    json.dump(all_pages_and_texts, json_file, ensure_ascii=False)




