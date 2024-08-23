import random
import glob
import json
from pylatexenc.latexwalker import LatexWalker
from tqdm.auto import tqdm  # for progress bars
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
    cleaned_text = text.replace("\n", " ").strip()  # Adjust as needed
    return cleaned_text


def split_exercise_sections(text: str) -> list[dict]:
    """
    Splits the text into exercises, options, and answers based on the provided patterns.

    Parameters:
        text (str): The plain text content.

    Returns:
        list[dict]: A list of dictionaries, each containing the exercise number, question, options, and answers.
    """
    # Updated Regex pattern
    exercise_pattern = re.compile(
        r'(?P<exercise_number>\d+\.\d+A?)\s*'  # Capture exercise number
        r'(?P<exercise_text>.+?)'              # Capture exercise text (non-greedy)
        r'(?P<answer_choices>(?:\s*[a-f]\)\s*.*?)*?)'  # Capture all answer choices
        r'(?=\d+\.\d+A?|$)',                   # Lookahead to next exercise or end of string
        re.DOTALL  # Enable dot to match newlines
    )

    # Regex to extract individual options
    options_pattern = re.compile(
        r'([a-f])\)\s*(.*?)\s*(?=\s*[a-f]\)|$)',  # Capture each option letter and text
        re.DOTALL
    )

    exercises = []

    # Iterate over each exercise match
    for match in exercise_pattern.finditer(text):
        exercise_number = match.group("exercise_number").strip()
        exercise_text = match.group("exercise_text").strip()
        answer_choices = match.group("answer_choices").strip()

        # Extract individual options
        options = []
        for opt_match in options_pattern.finditer(answer_choices):
            option_letter = opt_match.group(1).strip()
            option_text = opt_match.group(2).strip()
            options.append({
                "option_letter": option_letter,
                "option_text": option_text
            })

        exercises.append({
            "exercise_number": exercise_number,
            "exercise_text": exercise_text,
            "options": options
        })

    return exercises

def open_and_read_latex_exercises(latex_path: str) -> list[dict]:
    """
    Opens a LaTeX file, reads its content, and collects statistics.

    Parameters:
        latex_path (str): The file path to the LaTeX document to be opened and read.

    Returns:
        list[dict]: A list of dictionaries, each containing an exercise number, question, options, answers,
                    character count, word count, sentence count, token count, and the extracted text for each exercise.
    """
    with open(latex_path, "r", encoding="utf-8") as f:
        latex_content = f.read()

    text = latex_to_text(latex_content)
    text = text_formatter(text)

    exercises = split_exercise_sections(text)

    for exercise in exercises:
        exercise["char_count"] = len(exercise["exercise_text"])
        exercise["word_count"] = len(exercise["exercise_text"].split())
        exercise["sentence_count_raw"] = len(re.split(r'[.!?]+', exercise["exercise_text"]))  # Improved sentence count
        exercise["token_count"] = len(exercise["exercise_text"]) / 4  # Approximation

    return exercises

    return cleaned_text


def split_results_sections(text: str) -> list[dict]:
    """
    Splits the text into a list of dictionaries containing question numbers and their corresponding answers.

    Parameters:
        text (str): The plain text content.

    Returns:
        list[dict]: A list of dictionaries, each containing the question number and the correct answer.
    """
    # Define the regex pattern for extracting question numbers and answers
    results_pattern = re.compile(
        r'(?<!\d)(\d+)\s*([a-f])\)',
        # Matches question numbers followed by their corresponding answer (e.g., 1 d), 2 e), etc.)
        re.DOTALL
    )

    results = []

    # Find all matches for question number and answers
    for match in results_pattern.finditer(text):
        question_number = match.group(1).strip()
        correct_answer = match.group(2).strip()

        results.append({
            "question_number": question_number,
            "correct_answer": correct_answer
        })

    return results


def open_and_read_latex_results(latex_path: str) -> list[dict]:
    """
    Opens a LaTeX file, reads its content, and parses the results section.

    Parameters:
        latex_path (str): The file path to the LaTeX document to be opened and read.

    Returns:
        list[dict]: A list of dictionaries, each containing the question number and the correct answer.
    """
    with open(latex_path, "r", encoding="utf-8") as f:
        latex_content = f.read()

    text = latex_to_text(latex_content)
    text = text_formatter(text)
    print(text)

    results = split_results_sections(text)

    return results




# Define the path to the LaTeX files
latex_exercise_files = glob.glob("latex_docs/Exercitii.tex")
all_exercises = []

# Process each LaTeX file
for latex_file in latex_exercise_files:
    exercises = open_and_read_latex_exercises(latex_file)

    # Analyze each exercise with Spacy
    for item in tqdm(exercises, desc=f"Analyzing {latex_file}"):
        doc = item["exercise_text"]
        sentences = list(doc)

    all_exercises.extend(exercises)


latex_results_files = glob.glob("latex_docs/Raspunsuri.tex")
for latex_file in latex_results_files:
    results = open_and_read_latex_results(latex_file)
    all_exercises.extend(results)

# Define the output JSON file path
file_path = "teste_admitere_fizica.json"

# Write the extracted data to the JSON file
with open(file_path, "w", encoding="utf-8") as json_file:
    json.dump(all_exercises, json_file, ensure_ascii=False, indent=4)

print(f"Data extraction complete! Check '{file_path}' for the output.")
