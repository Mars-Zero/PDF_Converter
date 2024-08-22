import random
import spacy
from spacy.lang.ro import Romanian
import glob
import json
from pylatexenc.latexwalker import LatexWalker
from tqdm.auto import tqdm  # for progress bars, requires !pip install tqdm
import re


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


def split_sections(text: str):
    """
    Splits the text into exercises, options, and answers based on the provided patterns.

    Parameters:
        text (str): The plain text content.

    Returns:
        list[dict]: A list of dictionaries, each containing the exercise number, question, options, and answers.
    """
    # Patterns
    exercise_pattern = r'(\d+\.\d+[A-Z]?)\s+(.+?)(?=\n\d+\.\d+[A-Z]?|\n\\part|\n\\section|\Z)'
    options_pattern = r'([a-f])\)\s*(.*?)(?=(?:[a-f]\)|\n|$))'
    answer_explanation_pattern = r'(\d+)\s*([a-f])\)\s*(.*?)(?=(?:\d+\s*[a-f]\)|(?<!\d)\)\s+))'

    exercises = []

    # Find exercises
    for match in re.finditer(exercise_pattern, text, re.DOTALL):
        exercise_number, exercise_text = match.groups()

        # Find options within the exercise
        options = []
        for opt_match in re.finditer(options_pattern, exercise_text, re.DOTALL):
            option_letter, option_text = opt_match.groups()
            options.append({"option": option_letter, "text": option_text})

        # Find answers and explanations within the exercise
        answers = []
        for ans_match in re.finditer(answer_explanation_pattern, exercise_text, re.DOTALL):
            answer_number, answer_option, explanation = ans_match.groups()
            answers.append({"answer_number": answer_number, "answer_option": answer_option, "explanation": explanation})

        exercises.append({
            "exercise_number": exercise_number,
            "exercise_text": exercise_text,
            "options": options,
            "answers": answers
        })

    return exercises


def open_and_read_latex(latex_path: str) -> list[dict]:
    """
    Opens a LaTeX file, reads its content, and collects statistics.

    Parameters:
        latex_path (str): The file path to the LaTeX document to be opened and read.

    Returns:
        list[dict]: A list of dictionaries, each containing an exercise number, question, options, answers,
        character count, word count, sentence count, token count, and the extracted text for each exercise.
    """
    with open(latex_path, "r") as f:
        latex_content = f.read()

    text = latex_to_text(latex_content)
    text = text_formatter(text)

    exercises = split_sections(text)

    for exercise in exercises:
        exercise["char_count"] = len(exercise["exercise_text"])
        exercise["word_count"] = len(exercise["exercise_text"].split(" "))
        exercise["sentence_count_raw"] = len(exercise["exercise_text"].split(". "))
        exercise["token_count"] = len(exercise["exercise_text"]) / 4  # 1 token = ~4 chars

    return exercises


latex_files = glob.glob("latex_docs/cnv_2024_07_17_524f58412b42245c9921g.tex")
all_exercises = []

nlp = Romanian()

# Add a sentencizer pipeline, see https://spacy.io/api/sentencizer/
nlp.add_pipe("sentencizer")

for latex_file in latex_files:
    exercises = open_and_read_latex(latex_file)

    # Process the extracted text with Spacy
    for item in tqdm(exercises, desc=f"Analyzing {latex_file}"):
        item["sentences"] = list(nlp(item["exercise_text"]).sents)

        # Make sure all sentences are strings
        item["sentences"] = [str(sentence) for sentence in item["sentences"]]

        # Count the sentences
        item["sentence_count_spacy"] = len(item["sentences"])

    all_exercises.extend(exercises)

print(random.sample(all_exercises, k=1))

file_path = "teste_admitere_fizica.json"

# Write the list to the JSON file
with open(file_path, "w") as json_file:
    json.dump(all_exercises, json_file, ensure_ascii=False, indent=4)
