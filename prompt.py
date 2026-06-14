UOS_LINGUISTIC_PROMPT = """Extract exactly ONE sentence about the given aspect term from a hotel review.

Return a JSON array containing exactly ONE string. No explanation, no extra text.


## GOAL

The input has two parts:
- A sentence (may mention multiple targets)
- [aspect: X] — the target you must focus on

Extract only the clause that describes the aspect term X.
Ignore all other targets or opinions not related to X.


## RULES

1. Return ONLY the clause about [aspect: X]. Drop everything else.
2. Preserve the original words — do NOT paraphrase or substitute any word.
3. Make the clause a complete standalone sentence if it is a fragment:
   - Add "The" or "A" if missing
   - Add a copula ("is", "was", "are", "were") if missing
4. Keep ALL opinions about X in one clause — do NOT split by sentiment.
5. Never invent words, adjectives, or sentiments not in the input.


## EXAMPLES

Input: "The room was clean but the breakfast was cold."
[aspect: room]
Output: ["The room was clean."]

Input: "The room was clean but the breakfast was cold."
[aspect: breakfast]
Output: ["The breakfast was cold."]

Input: "The room was spacious but noisy."
[aspect: room]
Output: ["The room was spacious but noisy."]

Input: "The breakfast was delicious but expensive."
[aspect: breakfast]
Output: ["The breakfast was delicious but expensive."]

Input: "Good service."
[aspect: service]
Output: ["Good service."]

Input: "Very comfortable room and bed."
[aspect: bed]
Output: ["Very comfortable bed."]

Input: "The room was lovely with a beautiful view and a large balcony."
[aspect: view]
Output: ["The view was beautiful."]

Input: "Lovely hotel room, good beds, nice staff."
[aspect: staff]
Output: ["Nice staff."]


Input:
{sentence}

Output:"""
