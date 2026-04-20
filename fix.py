import codecs
import re

with open('src/explainability/service.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('?200 crore', '₹200 crore')
text = text.replace('?{total_penalty} crore', '₹{total_penalty} crore')
text = text.replace('top_contributing_signal = "-"', 'top_contributing_signal = "—"')
text = text.replace('reason = "-"', 'reason = "—"')
text = text.replace('current processing activity - a deliberate', 'current processing activity — a deliberate')
text = text.replace('different purpose - even under', 'different purpose — even under')

# Fix literal '?' that was generated from '₹' in the template map
text = re.sub(r'([^a-zA-Z\d\s])\?([^a-zA-Z\d\s])', r'\1₹\2', text)
# Specifically "₹200 crore" or "₹{total_penalty} crore"
text = text.replace('?\\200', '₹200') # if somehow matched
text = text.replace('?{', '₹{')

with open('src/explainability/service.py', 'w', encoding='utf-8') as f:
    f.write(text)
