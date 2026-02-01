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
        
        # Look for images associated with this question
        # Check question_tag's parent and its siblings for wp-caption divs or img tags
        img_url = None
        parent = question_tag.parent
        
        # First, check siblings of the question_tag within the same parent (e.g., div inside same <p>)
        sibling = question_tag.find_next_sibling()
        while sibling:
            # Check for wp-caption div containing an image (often inside the same <p>)
            if sibling.name == 'div' and sibling.get('class') and 'wp-caption' in ' '.join(sibling.get('class', [])):
                img_tag = sibling.find('img')
                if img_tag and img_tag.get('src'):
                    img_url = img_tag.get('src')
                    break
            
            # Check for standalone img tag
            if sibling.name == 'img' and sibling.get('src'):
                img_url = sibling.get('src')
                break
            
            sibling = sibling.find_next_sibling()
        
        # If not found, check siblings of the parent element
        if not img_url and parent:
            sibling = parent.find_next_sibling()
            while sibling:
                # Stop if we hit the next question
                if sibling.name == 'p':
                    strong_or_b = sibling.find(['strong', 'b'])
                    if strong_or_b and question_pattern.match(strong_or_b.get_text().strip()):
                        break
                
                # Check for wp-caption div containing an image
                if sibling.name == 'div' and sibling.get('class') and 'wp-caption' in ' '.join(sibling.get('class', [])):
                    img_tag = sibling.find('img')
                    if img_tag and img_tag.get('src'):
                        img_url = img_tag.get('src')
                        break
                
                # Check for standalone img tag
                if sibling.name == 'img' and sibling.get('src'):
                    img_url = sibling.get('src')
                    break
                
                # Stop at ul (choices) or message_box (explanation)
                if sibling.name == 'ul':
                    break
                if sibling.name == 'div' and sibling.get('class') and 'message_box' in ' '.join(sibling.get('class', [])):
                    break
                    
                sibling = sibling.find_next_sibling()
        
        if img_url:
            question_data['img'] = img_url
        
        # Find the next ul element that contains the choices
        # Use find_next_sibling from the question tag's parent or the tag itself
        next_tag = question_tag.find_next_sibling()
        if not next_tag:
            if parent:
                next_tag = parent.find_next_sibling()
        
        choices = []
        correct_answers = []
        pre_content = None  # Store any <pre> tag content
        
        # Try to find choices in a <ul> tag
        current_element = next_tag
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
                        colored_tag = li.find(['span', 'strong'], style=lambda x: x and 'color:' in x)
                        if colored_tag:
                            correct_answers.append(choice_text)
                        elif li.get('class') and 'correct_answer' in li.get('class'):
                            correct_answers.append(choice_text)
                break
            elif current_element.name == 'p' and question_pattern.match(current_element.get_text().strip()):
                break
            elif current_element.name == 'pre':
                if not pre_content:
                    raw_text = current_element.get_text()
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    pre_content = '\n'.join(lines)
            
            current_element = current_element.find_next_sibling()

        # If no choices found in <ul>, look for <br> separated choices in the same parent (e.g., Q16)
        if not choices:
            # Look at siblings of the question_tag (including text nodes)
            sibling = question_tag.next_sibling
            temp_choices = []
            while sibling:
                # If we hit another question tag or a different block element that's not a choice
                if sibling.name in ['p', 'div', 'hr'] and sibling.get_text().strip() and question_pattern.match(sibling.get_text().strip()):
                    break
                
                # If it's a tag like span or strong with color, it might be the answer
                if sibling.name in ['span', 'strong', 'b', 'i']:
                    text = clean_text(sibling.get_text())
                    if text:
                        temp_choices.append(text)
                        colored_tag = sibling if (sibling.get('style') and 'color:' in sibling.get('style')) else sibling.find(['span', 'strong'], style=lambda x: x and 'color:' in x)
                        if colored_tag:
                            correct_answers.append(text)
                
                # If it's a text node
                elif isinstance(sibling, str) or sibling.name is None:
                    text = clean_text(str(sibling))
                    if text:
                        temp_choices.append(text)
                
                # If we see a message box or explanation, stop
                if sibling.name == 'div' and ('message_box' in (sibling.get('class') or []) or 'explanation' in sibling.get_text().lower()):
                    break
                    
                sibling = sibling.next_sibling
            
            # Clean up temp_choices (filter out empty strings)
            choices = [c for c in temp_choices if c and len(c) > 0]
            # Since we collected pieces of text, we might need to regroup them. 
            # But the logic above might be too aggressive. 
            # In Q16, they are separated by <br>.
            # Let's re-evaluate Q16 structure:
            # @@<br /> /dev/null<br /> <span...>+</span><br /> –<br />
            # The next_sibling of 16-strong is <br/>, then text "@@", then <br/>, etc.
            
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

def validate_questions(questions, output_file_path):
    """Validate extracted questions (inline quality check)"""
    import urllib.parse
    
    def is_valid_url(url):
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    print("\n" + "=" * 60)
    print("🔍 QUALITY VALIDATION")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    for i, question in enumerate(questions, 1):
        question_errors = []
        question_warnings = []
        
        # Check if question has required fields
        if 'question' not in question:
            question_errors.append("Missing 'question' field")
        else:
            question_text = question['question'].strip()
            if len(question_text) <= 5:
                question_errors.append(f"Question too short ({len(question_text)} chars)")
        
        # Check choices and answers
        choices = question.get('choices', [])
        answer = question.get('answer')
        question_type = question.get('type', 'regular')
        
        if len(choices) > 0:
            if not answer:
                question_errors.append("Has choices but no answer key")
            elif answer == "Unknown":
                question_errors.append("Answer is 'Unknown'")
            
            if answer and answer != "Unknown" and question_type != 'special':
                if isinstance(answer, list):
                    for ans in answer:
                        if ans not in choices:
                            question_errors.append(f"Answer not in choices")
                else:
                    if answer not in choices:
                        question_errors.append(f"Answer not in choices")
        
        # Check image URLs
        if 'img' in question:
            if not is_valid_url(question['img']):
                question_errors.append(f"Invalid image URL")
        
        if question_errors:
            error_msg = f"Q{i}: {'; '.join(question_errors)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
        
        if question_warnings:
            warning_msg = f"Q{i}: {'; '.join(question_warnings)}"
            warnings.append(warning_msg)
            print(f"⚠️  {warning_msg}")
    
    # Summary
    if not errors and not warnings:
        print("✅ All validations passed!")
    else:
        if errors:
            print(f"\n❌ Found {len(errors)} error(s)")
        if warnings:
            print(f"⚠️  Found {len(warnings)} warning(s)")
    
    return len(errors) == 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python qs_extract_ccna.py <html_file_path>")
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
    input_name = html_file_path.stem
    
    if 'html' in str(html_file_path.parent):
        output_dir = Path(str(html_file_path.parent).replace('html', 'json'))
    else:
        output_dir = html_file_path.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = output_dir / f"{input_name}.json"
    
    # Write JSON output
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Extracted {len(questions)} questions")
        print(f"📝 Saved to: {output_file_path}")
        
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        sys.exit(1)
    
    # Run quality validation
    success = validate_questions(questions, output_file_path)
    
    if success:
        print(f"\n🎉 Done! {output_file_path.name}")
    else:
        print(f"\n⚠️  Completed with issues: {output_file_path.name}")
        sys.exit(1)

if __name__ == "__main__":
    main()