import random
import spacy
from spacy.lang.ro import Romanian
import glob
import json
from pylatexenc.latexwalker import LatexWalker


def latex_to_text(latex: str) -> str:
    """
    Extracts plain text from LaTeX input using LatexWalker.

    Parameters:
        latex (str): The LaTeX content as a string.

    Returns:
        str: The extracted plain text.
    """
    w = LatexWalker(latex)
    nodelist, pos, len_ = w.get_latex_nodes(pos=0)

    extracted_text = []
    for node in nodelist:
        if hasattr(node, 'nodelist'):
            for subnode in node.nodelist:
                extracted_text.append(subnode.latex_verbatim())
        else:
            extracted_text.append(node.latex_verbatim())

    return ''.join(extracted_text)


def text_formatter(text: str) -> str:
    """Performs minor formatting on text."""
    cleaned_text = text.replace("\n", " ").strip()  # note: this might be different for each doc (best to experiment)
    return cleaned_text


def open_and_read_latex(latex_path: str) -> list[dict]:
    """
    Opens a LaTeX file, reads its content, and collects statistics.

    Parameters:
        latex_path (str): The file path to the LaTeX document to be opened and read.

    Returns:
        list[dict]: A list of dictionaries, each containing a simulated page number,
        character count, word count, sentence count, token count, and the extracted text
        for each simulated page.
    """
    with open(latex_path, "r") as f:
        latex_content = f.read()

    text = latex_to_text(latex_content)
    text = text_formatter(text)

    # Simulate page-like chunks if necessary, here we assume the whole content as one page
    pages_and_texts = [{"page_number": 0,
                        "page_char_count": len(text),
                        "page_word_count": len(text.split(" ")),
                        "page_sentence_count_raw": len(text.split(". ")),
                        "page_token_count": len(text) / 4,
                        # 1 token = ~4 chars, see: https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
                        "text": text}]

    return pages_and_texts


latex_files = glob.glob("latex_docs/Fizica/*.tex")
all_pages_and_texts = []

nlp = Romanian()

# Add a sentencizer pipeline, see https://spacy.io/api/sentencizer/
nlp.add_pipe("sentencizer")

for latex_file in latex_files:
    pages_and_texts = open_and_read_latex(latex_file)

    # Process the extracted text with Spacy
    for item in tqdm(pages_and_texts, desc=f"Analyzing {latex_file}"):
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
