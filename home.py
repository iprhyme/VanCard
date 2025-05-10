import streamlit as st
import pdfplumber
from groq import Groq
import re
import streamlit.components.v1 as components
from math import ceil

st.set_page_config(
    page_title="VanCard ",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === Set your Groq API key ===
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# === Initialize Groq client ===
client = Groq(api_key=GROQ_API_KEY)

# === UI ===
with st.sidebar:
    st.sidebar.write("Developed by Yazeed")
    with st.expander("Contacts Information"):
        st.markdown("[Twitter](https://x.com/_YazeedA)")
        st.markdown("[LinkedIn](https://www.linkedin.com/in/yazeed-alobaidan-218b4a2b4/)")
        st.markdown("[GitHub](https://github.com/iprhyme)")

st.title("VanCard - AI Flashcards Generator")
st.subheader("Generate Flashcards from PDF")

uploaded_file = st.file_uploader(" Upload a PDF file", type=["pdf"])
num_cards = st.slider(" How many flashcards do you want?", 1, 20, 5)

# Extract flashcards from LLM output
def extract_mcq_flashcards(raw_output):
    cards = []
    blocks = re.split(r"Q:\s*", raw_output)[1:]  # skip first empty split
    for block in blocks:
        try:
            q_match = re.search(r"^(.*?)\nOptions:", block, re.DOTALL)
            options_match = re.findall(r"([A-D])\.\s*(.+)", block)
            answer_match = re.search(r"Answer:\s*([A-D])", block)

            if q_match and options_match and answer_match:
                question = q_match.group(1).strip()
                if len(question.split()) < 5:  # filter too short questions
                    continue
                
                options = {letter: text.strip() for letter, text in options_match}
                correct = answer_match.group(1).strip()

                cards.append({
                    "question": question,
                    "options": options,
                    "answer": correct
                })
        except:
            continue
    return cards

# Render individual flashcard as HTML + JS
def render_mcq_flashcard(index, card, total_cards):
    correct_letter = card['answer']
    options = card['options']
    question_id = f"q{index}"

    options_html = ""
    for letter, text in options.items():
        options_html += f"""
        <div class="option" id="opt-{question_id}-{letter}" onclick="selectAnswer('{question_id}', '{letter}', '{correct_letter}', {index}, {total_cards})">
            <b>{letter}.</b> {text}
        </div>
        """

    html = f"""
    <div class="flashcard slide-in">
        <div class="title">Flashcard {index}</div>
        <div class="question">{card['question']}</div>
        {options_html}
    </div>
    """
    return html



# Function to create JavaScript for answering and scoring
def create_answer_script(total_cards):
    script = f"""
    <script>
    // Initialize tracking arrays if not already done
    if (typeof window.userAnswers === 'undefined') {{
        window.userAnswers = Array({total_cards}).fill(null);
        window.totalAnswered = 0;
        window.answeredQuestions = {{}};
    }}
    
    function selectAnswer(questionId, selected, correct, qIndex, totalQuestions) {{
        // Check if already answered
        if (window.answeredQuestions[questionId]) return;
        
        // Mark as answered
        window.answeredQuestions[questionId] = true;
        
        var selectedEl = document.getElementById("opt-" + questionId + "-" + selected);
        var correctEl = document.getElementById("opt-" + questionId + "-" + correct);
        
        // Store if answer was correct
        window.userAnswers[qIndex-1] = (selected === correct) ? 1 : 0;
        window.totalAnswered++;
        
        // Visual feedback
        if (selected === correct) {{
            selectedEl.style.backgroundColor = "#e6f4ea";
            selectedEl.style.color = "#137333";
            selectedEl.style.fontWeight = "bold";
        }} else {{
            selectedEl.style.backgroundColor = "#fdecea";
            selectedEl.style.color = "#d93025";
            correctEl.style.backgroundColor = "#e6f4ea";
            correctEl.style.color = "#137333";
            correctEl.style.fontWeight = "bold";
        }}
        
        // Check if all questions have been answered
        if (window.totalAnswered === totalQuestions) {{
            // Calculate score
            var correctCount = 0;
            for (var i = 0; i < window.userAnswers.length; i++) {{
                correctCount += window.userAnswers[i] || 0;
            }}
            var percentage = Math.round((correctCount / totalQuestions) * 100);
            
            // Build feedback
            var feedbackHtml = '';
            if (percentage >= 90) {{
                feedbackHtml = '<p class="feedback excellent">Excellent!</p>';
            }} else if (percentage >= 70) {{
                feedbackHtml = '<p class="feedback good">You have a solid understanding!</p>';
            }} else if (percentage >= 50) {{
                feedbackHtml = '<p class="feedback average">Not bad. Some review might help.</p>';
            }} else {{
                feedbackHtml = '<p class="feedback needs-work">You need more practice. Review the material again.</p>';
            }}
            
            // Create and show score section
            var scoreHtml = '<div class="score-card">' +
                '<h2>Quiz Complete!</h2>' +
                '<div class="score-info">' +
                '<p>You scored <span class="score-highlight">' + correctCount + '/' + totalQuestions + '</span></p>' +
                '<p>Percentage: <span class="score-highlight">' + percentage + '%</span></p>' +
                '</div>' +
                feedbackHtml +
                '</div>';
            
            // Create score section at the end of all flashcards
            var newScoreSection = document.createElement('div');
            newScoreSection.id = 'score-section';
            newScoreSection.innerHTML = scoreHtml;
            newScoreSection.style.marginTop = '40px';
            
            // Get the last flashcard and append score section after it
            var flashcards = document.getElementsByClassName('flashcard');
            var lastFlashcard = flashcards[flashcards.length - 1];
            lastFlashcard.parentNode.insertBefore(newScoreSection, lastFlashcard.nextSibling);
            
            // Scroll to score section
            newScoreSection.scrollIntoView({{ behavior: 'smooth' }});
        }}
    }}
    </script>
    """
    return script

# Add CSS for flashcards and score section
def get_flashcard_css():
    return """
    <style>
        .flashcard {
            background-color: #ffffff;
            color: #15668f;
            padding: 20px;
            border-radius: 16px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.08);
            margin-bottom: 30px;
            max-width: 700px;
            border-left: 12px solid #97CAF5;
            font-family: 'Segoe UI', sans-serif;
            animation: slideIn 0.5s ease-out;
        }
        .title { font-size: 20px; font-weight: 700; margin-bottom: 10px; }
        .question { font-size: 17px; font-weight: 600; margin-bottom: 15px; }
        .option {
            margin-top: 8px;
            padding: 12px;
            border-radius: 8px;
            background-color: #f1f3f4;
            color: #3c4043;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
        }
        .option:hover { background-color: #e3e3e3; transform: scale(1.02); }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        #score-section {
            margin-top: 40px;
            padding-top: 20px;
        }
        .score-card {
            background-color: #ffffff;
            color: #15668f;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.5);
            max-width: 700px;
            border-left: 12px solid #019a63;
            font-family: 'Segoe UI', sans-serif;
            animation: fadeIn 3s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .score-card h2 {
            font-size: 28px;
            margin-bottom: 20px;
            color: #15668f;
        }
        .score-info {
            font-size: 20px;
            margin-bottom: 20px;
        }
        .score-highlight {
            font-weight: bold;
            font-size: 24px;
            color: #15668f;
        }
        .feedback {
            font-size: 18px;
            padding: 10px;
            border-radius: 8px;
        }
        .excellent {
            background-color: #e6f4ea;
            color: #137333;
        }
        .good {
            background-color: #e8f0fe;
            color: #1a73e8;
        }
        .average {
            background-color: #fef7e0;
            color: #b06000;
        }
        .needs-work {
            background-color: #fdecea;
            color: #d93025;
        }
    </style>
    """

# Split PDF into overlapping chunks
def split_pdf_into_overlapping_chunks(pages, chunk_size=2, overlap=1):
    chunks = []
    for i in range(0, len(pages), chunk_size - overlap):
        chunk_text = "\n".join([page.extract_text() or "" for page in pages[i:i+chunk_size]])
        if chunk_text.strip():
            chunks.append(chunk_text)
    return chunks

# === Main Execution ===
if uploaded_file:
    if st.button("Generate Flashcards"):
        with pdfplumber.open(uploaded_file) as pdf:
            chunks = split_pdf_into_overlapping_chunks(pdf.pages, chunk_size=3, overlap=1)
        all_cards = []

        # Distribute number of cards per chunk
        cards_distribution = [num_cards // len(chunks)] * len(chunks)
        for i in range(num_cards % len(chunks)):
            cards_distribution[i] += 1

        with st.spinner("Generating flashcards..."):
            for chunk, count in zip(chunks, cards_distribution):
                prompt = f"""
You are a helpful assistant. Generate {count} high-quality educational flashcards in multiple-choice format based on the following text.

Ensure each question is clear, useful, EDUCUTIONAL, and contextually relevant.
Do not generate questions based on irrelevant or trivial details.
Make sure that each question is fully self-contained and does not refer to an arbitrary object (like an article or blog).
We need each question to be in its own context.

Each flashcard should include:
1. A clear, educational question.
2. 3 to 4 realistic answer options.
3. One correct answer (clearly marked).

Use this format exactly:
Q: [Question]
Options:
A. option 1
B. option 2
C. option 3
D. option 4 (if applicable)
Answer: Correct letter

Only return flashcards. No extra commentary.
Text:
{chunk}
"""
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                )
                raw_output = response.choices[0].message.content
                cards = extract_mcq_flashcards(raw_output)
                all_cards.extend(cards)

        st.markdown("---")
        all_cards = all_cards[:num_cards]  # Cap at requested count
        
         # Start with the CSS and JavaScript
        flashcard_html = get_flashcard_css()
        flashcard_html += create_answer_script(len(all_cards))
        
        # Add all flashcards HTML - no score section here anymore
        for i, card in enumerate(all_cards, 1):
            flashcard_html += render_mcq_flashcard(i, card, len(all_cards))
        
        # The score section will be dynamically added after the last flashcard
        # in the JavaScript when the quiz is complete
            
        # Render everything at once
        components.html(flashcard_html, height=373 * (len(all_cards)+1), scrolling=True)