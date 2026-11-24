import re
import unicodedata


def fold(value):
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def title_matches_word(title, word):
    normalized = " ".join("".join(char if char.isalnum() else " " for char in fold(title)).split())
    query = " ".join("".join(char if char.isalnum() else " " for char in fold(word)).split())
    if not query:
        return False
    if query in normalized:
        return True
    limit = 2 if len(query) >= 6 else 1 if len(query) >= 3 else 0
    for token in normalized.split():
        if token.startswith(query) or (len(query) >= 3 and query in token):
            return True
        if abs(len(token) - len(query)) > limit:
            continue
        previous = list(range(len(token) + 1))
        for row, query_char in enumerate(query, 1):
            current = [row]
            for column, title_char in enumerate(token, 1):
                current.append(min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (query_char != title_char),
                ))
            previous = current
        if previous[-1] <= limit:
            return True
    return False


def query_words(query):
    return re.findall(r"\S+", fold(query))


def work_matches(artist_name, title, description, words):
    haystack = fold(f"{artist_name} {title} {description}")
    return all(word in haystack or title_matches_word(title, word) for word in words)
