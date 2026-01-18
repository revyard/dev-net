#!/usr/bin/env python3
"""
HTML Quiz Parser - Extracts quiz questions from HTML and converts to JSON format

This script automatically installs required dependencies (beautifulsoup4) if not present.
No manual dependency installation required!

Usage: python3 html_to_json_parser.py <html_file_path>
Example: python3 html_to_json_parser.py assets/html/checkpoint1.html
"""

import re
import json
import sys
import subprocess
from pathlib import Path
import html

# Auto-install dependencies
def install_dependencies():
    """Install required dependencies if not available"""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup
    except ImportError:
        print("BeautifulSoup4 not found. Installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4'])
            print("Successfully installed beautifulsoup4")
            from bs4 import BeautifulSoup
            return BeautifulSoup
        except subprocess.CalledProcessError:
            print("Failed to install beautifulsoup4. Please install manually with:")
            print("pip install beautifulsoup4")
            sys.exit(1)
        except ImportError:
            print("Error: Could not import BeautifulSoup4 after installation.")
            print("Please install manually with: pip install beautifulsoup4")
            sys.exit(1)

# Install dependencies and get BeautifulSoup
BeautifulSoup = install_dependencies()

def clean_text(text):
    """Clean HTML entities and extra whitespace from text"""
    if not text:
        return ""
    # Decode HTML entities
    text = html.unescape(text)
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_quiz_data(html_content):
    """Extract quiz questions, choices, and answers from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    questions = []
    
    # Find all question paragraphs that start with a number
    question_pattern = re.compile(r'^\d+\.\s+')
    
    # Strategy: Find ALL strong/b tags that match question pattern first
    # Then process them in order of appearance
    question_elements = []
    seen_questions = set()  # Track question numbers we've already found
    
    # Find all strong/b tags that look like questions
    for tag in soup.find_all(['strong', 'b']):
        tag_text = tag.get_text().strip()
        if question_pattern.match(tag_text):
            # Extract the question number to avoid duplicates
            match = re.match(r'^(\d+)\.', tag_text)
            if match:
                q_num = int(match.group(1))
                if q_num not in seen_questions:
                    seen_questions.add(q_num)
                    question_elements.append(tag)
    
    # Also check paragraphs that contain questions in a different structure
    for p_tag in soup.find_all('p'):
        strong_tag = p_tag.find('strong') or p_tag.find('b')
        if strong_tag:
            tag_text = strong_tag.get_text().strip()
            if question_pattern.match(tag_text):
                match = re.match(r'^(\d+)\.', tag_text)
                if match:
                    q_num = int(match.group(1))
                    if q_num not in seen_questions:
                        seen_questions.add(q_num)
                        question_elements.append(strong_tag)
    
    # Sort question elements by their question number
    def get_question_number(tag):
        text = tag.get_text().strip()
        match = re.match(r'^(\d+)\.', text)
        return int(match.group(1)) if match else 0
    
    question_elements.sort(key=get_question_number)
    
    # Now use the sorted question elements as our processing list
    all_elements = question_elements
    
    i = 0
    while i < len(all_elements):
        element = all_elements[i]
        # All elements are now strong/b tags containing questions
        question_tag = element
        
        # Extract question text
        question_text = clean_text(question_tag.get_text())
        
        question_data = {}
        question_data['question'] = question_text
        
        # Find the next ul element that contains the choices
        # Use find_next_sibling from the question tag's parent or the tag itself
        current_element = question_tag.find_next_sibling()
        if not current_element:
            # If no sibling, try parent's next sibling
            parent = question_tag.parent
            if parent:
                current_element = parent.find_next_sibling()
        
        choices = []
        correct_answers = []
        pre_content = None  # Store any <pre> tag content
        
        while current_element:
            if current_element.name == 'ul':
                # Found the choices list
                li_elements = current_element.find_all('li')
                
                for li in li_elements:
                    # Extract choice text (remove HTML tags but keep content)
                    choice_text = clean_text(li.get_text())
                    if choice_text:  # Only add non-empty choices
                        choices.append(choice_text)
                        
                        # Check if this is a correct answer
                        # Look for any span or strong tag with color styling (any color means it's the answer)
                        colored_tag = li.find(['span', 'strong'], style=lambda x: x and 'color:' in x)
                        if colored_tag:
                            correct_answers.append(choice_text)
                        # Also check for li elements with class="correct_answer"
                        elif li.get('class') and 'correct_answer' in li.get('class'):
                            correct_answers.append(choice_text)
                
                break
            elif current_element.name == 'p':
                # Check if this is part of the current question or the next question
                strong_or_b = current_element.find('strong') or current_element.find('b')
                if strong_or_b:
                    strong_text = strong_or_b.get_text().strip()
                    # If it starts with a number followed by a dot, it's a new question
                    if question_pattern.match(strong_text):
                        break
            elif current_element.name == 'pre':
                # Capture pre tag content with preserved line breaks
                if not pre_content:  # Only capture the first pre tag
                    # Get raw text and preserve line breaks, but clean up extra whitespace
                    raw_text = current_element.get_text()
                    # Split by lines, strip each line, and rejoin with newlines
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    pre_content = '\n'.join(lines)
            elif current_element.name in ['div', 'img', 'strong', 'b']:
                # Skip these elements but continue looking for choices
                pass
            
            current_element = current_element.find_next_sibling()
        
        # Add pre content if found
        if pre_content:
            question_data['pre'] = pre_content
        
        # Add question if we found choices, or if it's a special question type
        if choices:
            question_data['choices'] = choices
            
            # Set answer format based on number of correct answers
            if len(correct_answers) == 1:
                question_data['answer'] = correct_answers[0]
            elif len(correct_answers) > 1:
                question_data['answer'] = correct_answers
            else:
                # If no correct answer found, mark as unknown
                question_data['answer'] = "Unknown"
            
            questions.append(question_data)
        else:
            # Check if this is a special question type (matching, image-based, etc.)
            question_text_lower = question_text.lower()
            if any(keyword in question_text_lower for keyword in ['match', 'question as presented', 'refer to the exhibit']):
                question_data['type'] = 'special'
                question_data['choices'] = []
                question_data['answer'] = "See image for the answer"
                questions.append(question_data)
        
        i += 1
    
    return questions

def main():
    if len(sys.argv) != 2:
        print("Usage: python html_to_json_parser.py <html_file_path>")
        sys.exit(1)
    
    html_file_path = Path(sys.argv[1])
    
    if not html_file_path.exists():
        print(f"Error: File {html_file_path} does not exist")
        sys.exit(1)
    
    # Read HTML content
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        sys.exit(1)
    
    # Extract quiz data
    questions = extract_quiz_data(html_content)
    
    # Determine output file path
    # If input is assets/html/checkpointX.html, output should be assets/json/checkpointX.json
    input_name = html_file_path.stem  # Gets filename without extension
    
    if 'html' in str(html_file_path.parent):
        # Replace 'html' with 'json' in the path
        output_dir = Path(str(html_file_path.parent).replace('html', 'json'))
    else:
        # Same directory as input
        output_dir = html_file_path.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / f"{input_name}.json"
    
    # Write JSON output
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully extracted {len(questions)} questions")
        print(f"Output saved to: {output_file_path}")
        
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()