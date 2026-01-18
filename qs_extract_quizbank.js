const fs = require('fs');
const { JSDOM } = require('jsdom');
const path = require('path');

// Get checkpoint filename from command line argument
const checkpointName = process.argv[2];

if (!checkpointName) {
  console.error('❌ Please provide a checkpoint name: node extractCheckpoint.js <name>');
  console.error('   Example: node extractCheckpoint.js checkpoint1.2');
  process.exit(1);
}

const htmlPath = `./assets/html/${checkpointName}.html`;
const jsonPath = `./assets/json/${checkpointName}.json`;

// Check if HTML file exists
if (!fs.existsSync(htmlPath)) {
  console.error(`❌ File not found: ${htmlPath}`);
  process.exit(1);
}

const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
const dom = new JSDOM(htmlContent);
const document = dom.window.document;

// Get stats from HTML - find by label text
const statCards = document.querySelectorAll('.stat-card');
const stats = {
  total: 0,
  correct: 0,
  wrong: 0,
  new: 0
};

statCards.forEach(card => {
  const label = card.querySelector('.stat-label');
  const value = card.querySelector('.stat-value');
  if (label && value) {
    const labelText = label.textContent.toLowerCase();
    const numValue = parseInt(value.textContent) || 0;
    if (labelText.includes('total')) stats.total = numValue;
    else if (labelText.includes('correct')) stats.correct = numValue;
    else if (labelText.includes('wrong')) stats.wrong = numValue;
    else if (labelText.includes('new')) stats.new = numValue;
  }
});

// Extract all questions
const questionElements = document.querySelectorAll('.display_question');
const extractedQuestions = [];

questionElements.forEach((questionEl) => {
  try {
    // Get question text
    const questionTextEl = questionEl.querySelector('.question_text');
    if (!questionTextEl) return;

    // Extract the text content, removing the badge elements
    const questionTextClone = questionTextEl.cloneNode(true);
    const badgeClone = questionTextClone.querySelector('.answer-source-badge');
    if (badgeClone) {
      badgeClone.remove();
    }
    let questionText = questionTextClone.textContent.trim();

    // Check if there's an image in the question
    const imgEl = questionTextEl.querySelector('img');
    let imgSrc = null;
    if (imgEl) {
      imgSrc = imgEl.getAttribute('src');
    }

    // Get all answer choices
    const answerLabels = questionEl.querySelectorAll('.answer_label');
    const choices = [];
    const correctAnswers = [];

    answerLabels.forEach((answerLabel) => {
      // Get the choice text
      const choiceTextNode = answerLabel.cloneNode(true);
      // Remove any badges from the choice text
      const badges = choiceTextNode.querySelectorAll('.correct-answer-badge, .wrong-answer-badge');
      badges.forEach(badge => badge.remove());
      const choiceText = choiceTextNode.textContent.trim();

      if (choiceText) {
        choices.push(choiceText);

        // Check if this is a correct answer
        const correctBadge = answerLabel.parentElement.querySelector('.correct-answer-badge');
        if (correctBadge) {
          correctAnswers.push(choiceText);
        }
      }
    });

    // Only add questions that have at least one correct answer
    if (correctAnswers.length > 0 && choices.length > 0) {
      const questionObj = {
        question: questionText
      };

      // Add image if present
      if (imgSrc) {
        questionObj.img = imgSrc;
      }

      questionObj.choices = choices;

      // If multiple correct answers, use array, otherwise use string
      if (correctAnswers.length > 1) {
        questionObj.answer = correctAnswers;
      } else {
        questionObj.answer = correctAnswers[0];
      }

      extractedQuestions.push(questionObj);
    }
  } catch (error) {
    console.error('Error processing question:', error);
  }
});

// Write to JSON file
fs.writeFileSync(jsonPath, JSON.stringify(extractedQuestions, null, 2), 'utf-8');

// Display results
console.log(`\n📊 ${checkpointName} - Comparison:`);
console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
console.log(`HTML Stats:`);
console.log(`  Total Questions:        ${stats.total}`);
console.log(`  ✅ Correct Answers:     ${stats.correct}`);
console.log(`  🚫 Wrong Answers:       ${stats.wrong}`);
console.log(`  ✨ New/Partial/Unknown: ${stats.new}`);
console.log(`\nExtracted:`);
console.log(`  Questions in JSON:      ${extractedQuestions.length}`);
console.log(`\n✅ Match: ${extractedQuestions.length === stats.correct ? 'PERFECT ✓' : 'MISMATCH ✗'}`);
console.log(`📝 Updated: ${jsonPath}`);
console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
