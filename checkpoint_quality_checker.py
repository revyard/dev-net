#!/usr/bin/env python3
"""
Checkpoint JSON Quality Checker

This script validates the quality of checkpoint JSON files by checking:
1. If choices > 0, there should be an answer key and is not "Unknown"
2. If there are images, they should be valid URLs
3. Questions should be longer than 5 characters
4. Answer(s) should exist in choices (for non-special questions)

Usage: python3 checkpoint_quality_checker.py <json_file>
Example: python3 checkpoint_quality_checker.py assets/json/checkpoint1.json
"""

import json
import sys
import re
import urllib.parse
from pathlib import Path

def is_valid_url(url):
    """Check if a URL is properly formatted"""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_checkpoint_json(json_file_path):
    """Validate a checkpoint JSON file"""
    
    print(f"🔍 Validating: {json_file_path}")
    print("=" * 60)
    
    # Load JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return False
    
    if not isinstance(questions, list):
        print("❌ JSON should contain a list of questions")
        return False
    
    total_questions = len(questions)
    print(f"📊 Total questions in JSON: {total_questions}")
    
    print("\n🔍 Detailed validation:")
    print("-" * 40)
    
    errors = []
    warnings = []
    
    for i, question in enumerate(questions, 1):
        question_errors = []
        question_warnings = []
        
        # Check if question has required fields
        if 'question' not in question:
            question_errors.append("Missing 'question' field")
        else:
            # Check question length
            question_text = question['question'].strip()
            if len(question_text) <= 5:
                question_errors.append(f"Question too short ({len(question_text)} chars): '{question_text}'")
        
        # Check choices and answers
        choices = question.get('choices', [])
        answer = question.get('answer')
        question_type = question.get('type', 'regular')
        
        # Rule 1: If choices > 0, there should be an answer key and is not "Unknown"
        if len(choices) > 0:
            if not answer:
                question_errors.append("Has choices but no answer key")
            elif answer == "Unknown":
                question_errors.append("Answer is 'Unknown'")
            
            # Rule 5: Answer(s) should exist in choices (for non-special questions)
            if answer and answer != "Unknown" and question_type != 'special':
                if isinstance(answer, list):
                    # Multiple answers
                    for ans in answer:
                        if ans not in choices:
                            question_errors.append(f"Answer '{ans}' not found in choices")
                else:
                    # Single answer
                    if answer not in choices:
                        question_errors.append(f"Answer '{answer}' not found in choices")
        
        # Rule 3: If there are images, they should be valid URLs
        if 'img' in question:
            img_url = question['img']
            if not is_valid_url(img_url):
                question_errors.append(f"Invalid image URL: '{img_url}'")
        
        # Check for special questions
        if question_type == 'special':
            if len(choices) > 0:
                question_warnings.append("Special question has choices (should be empty)")
            if answer != "See image for the answer":
                question_warnings.append("Special question should have answer 'See image for the answer'")
        
        # Report errors and warnings for this question
        if question_errors:
            error_msg = f"Question {i}: {'; '.join(question_errors)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
        
        if question_warnings:
            warning_msg = f"Question {i}: {'; '.join(question_warnings)}"
            warnings.append(warning_msg)
            print(f"⚠️  {warning_msg}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    if not errors and not warnings:
        print("✅ All validations passed! The JSON file is high quality.")
        return True
    else:
        if errors:
            print(f"❌ Found {len(errors)} error(s):")
            for error in errors:
                print(f"   • {error}")
        
        if warnings:
            print(f"⚠️  Found {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"   • {warning}")
        
        return len(errors) == 0  # Return True if no errors (warnings are OK)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 checkpoint_quality_checker.py <json_file>")
        print("Example: python3 checkpoint_quality_checker.py assets/json/checkpoint1.json")
        sys.exit(1)
    
    json_file_path = Path(sys.argv[1])
    
    if not json_file_path.exists():
        print(f"❌ JSON file not found: {json_file_path}")
        sys.exit(1)
    
    success = validate_checkpoint_json(json_file_path)
    
    if success:
        print(f"\n🎉 Validation completed successfully for {json_file_path.name}")
        sys.exit(0)
    else:
        print(f"\n💥 Validation failed for {json_file_path.name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
