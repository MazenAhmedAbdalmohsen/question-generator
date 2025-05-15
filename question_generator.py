import openai
import json

def generate_questions(text, num_questions=14):
    prompt = f"""
    Generate {num_questions} questions from this text:
    {text[:3000]}  # Limiting context window

    Requirements:
    - 7 medium difficulty (MID) questions
    - 7 easy questions
    - Format as JSON list
    - Each question format:
    {{
        "question": "text",
        "options": ["A", "B", "C", "D"],
        "correct": "A",
        "difficulty": "easy|mid"
    }}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return []