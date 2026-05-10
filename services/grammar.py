import language_tool_python
import re

tool = language_tool_python.LanguageTool('en-US')

def analyze_grammar(text, filename):
    matches = tool.check(text)

    total_words = len(re.findall(r"\b\w+\b", text))
    mistake_count = len(matches)

    score = ((total_words - mistake_count) / total_words) * 100 if total_words else 0

    issues = []

    for match in matches:
        issues.append({
            "message": match.message,
            "suggestions": match.replacements,
            "offset": match.offset,
            "length": match.error_length
        })

    return {
        "file": filename,
        "mistakes": mistake_count,
        "total_words": total_words,
        "score": round(score, 2),
        "issues": issues,
        "original_text": text
    }