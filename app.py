import re

def fix_arabic_text(text):
    """Clean and normalize Arabic text"""
    if not text:
        return text
    
    # Normalize Arabic characters
    text = text.replace('ى', 'ي')
    text = text.replace('ك', 'ک')
    
    # Remove unwanted characters
    text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s]', '', text)
    
    # Fix common issues
    text = re.sub(r'(\s)ال(\S)', r'\1الـ\2', text)  # Fix ال التعريف
    text = re.sub(r'(\S)ـ(\S)', r'\1\2', text)  # Remove unnecessary tatweel
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text
