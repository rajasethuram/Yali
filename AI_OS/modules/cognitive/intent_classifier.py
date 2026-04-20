"""
Intent classifier for interview questions.
Classifies: behavioral / technical / leadership / situational / salary / general
"""
import re
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

INTENT_PATTERNS = {
    "behavioral": [
        r"tell me about (a time|yourself|your)",
        r"describe (a situation|an experience|a time)",
        r"give me an example",
        r"have you ever",
        r"what (did you|would you) do when",
        r"how (did you|do you) handle",
        r"walk me through",
        r"greatest (strength|weakness|achievement|challenge|failure)",
        r"why (did you|are you) (leave|leaving|want)",
        r"what (motivates|drives|inspired) you",
        r"biggest (mistake|failure|regret)",
        r"proud(est)? (moment|achievement|accomplishment)",
        r"conflict with",
        r"worked (under pressure|with difficult)",
        r"feedback (you|from)",
    ],
    "technical": [
        r"(design|implement|build|create) (a |an )?(system|service|api|database|architecture)",
        r"explain (how|the|what)",
        r"what is (a |an |the )?(difference|complexity|algorithm|data structure|design pattern)",
        r"(time|space) complexity",
        r"(sort|search|traverse|optimize)",
        r"(sql|nosql|database|query)",
        r"(thread|process|concurrency|async|parallel)",
        r"(rest|graphql|grpc|api|microservice)",
        r"(docker|kubernetes|container|deploy)",
        r"(cache|redis|memcache)",
        r"(big o|o\(n\)|o\(log)",
        r"code (review|quality|smell)",
        r"(debugging|debug|fix) (a |an |the )?bug",
        r"url shortener|parking lot|twitter|instagram|uber|whatsapp",
        r"(machine learning|neural network|model|train|classify)",
    ],
    "leadership": [
        r"(led|lead|leading|managed|manage) (a |the )?(team|project|initiative)",
        r"(mentored|mentor|coaching|trained) (a |an )?(junior|team member)",
        r"(stakeholder|executive|c-level)",
        r"(prioritize|prioritization|roadmap)",
        r"(influence without authority|cross-functional)",
        r"(difficult (team member|colleague|manager))",
        r"(strategy|strategic|vision)",
        r"(decision (making|under uncertainty))",
        r"(team (performance|building|culture))",
    ],
    "situational": [
        r"what would you do if",
        r"how would you (handle|approach|deal with)",
        r"imagine (you|a situation)",
        r"suppose (you|a client|your manager)",
        r"if you were",
        r"scenario (where|in which)",
        r"hypothetically",
    ],
    "salary": [
        r"(expected|current|desired) (salary|compensation|ctc|package)",
        r"how much (do you|are you) (make|earn|expect|looking)",
        r"(negotiate|negotiation|offer)",
        r"(notice period|joining)",
    ],
    "company": [
        r"why (do you want to|are you interested in) (join|work (at|for|with))",
        r"what do you know about (our company|us)",
        r"(5|five) years? (from now|plan|goal)",
        r"where do you see yourself",
        r"why should we hire you",
        r"questions? (for me|for us)",
    ],
}

INTENT_DISPLAY = {
    "behavioral": "Behavioral",
    "technical": "Technical",
    "leadership": "Leadership",
    "situational": "Situational",
    "salary": "Salary/Offer",
    "company": "Company/Role",
    "general": "General",
}


def classify_intent(text: str) -> Tuple[str, float, str]:
    """
    Returns (intent, confidence, display_label).
    confidence: 0.0–1.0 (pattern-based heuristic)
    """
    text_lower = text.lower().strip()
    scores = {intent: 0 for intent in INTENT_PATTERNS}

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                scores[intent] += 1

    total_matches = sum(scores.values())
    if total_matches == 0:
        return ("general", 0.5, INTENT_DISPLAY["general"])

    best_intent = max(scores, key=scores.get)
    confidence = min(scores[best_intent] / 3.0, 1.0)  # normalize: 3+ matches = 1.0

    return (best_intent, confidence, INTENT_DISPLAY[best_intent])


def get_response_framework(intent: str) -> str:
    """Returns the recommended answer framework for each intent type."""
    frameworks = {
        "behavioral": "STAR Method: Situation -> Task -> Action -> Result",
        "technical": "Structure: Clarify -> High-level design -> Deep dive -> Trade-offs -> Scale",
        "leadership": "Impact Method: Context -> Your role -> Actions taken -> Measurable outcome",
        "situational": "PREP Method: Position -> Reason -> Example -> Position (restate)",
        "salary": "Anchor high, show flexibility: Research range -> State expected CTC -> Justify with value",
        "company": "Show research: Know their product -> Link to your goals -> Ask smart question",
        "general": "PREP Method: Point -> Reason -> Example -> Point (restate)",
    }
    return frameworks.get(intent, frameworks["general"])


if __name__ == "__main__":
    test_questions = [
        "Tell me about a time you handled a conflict with a teammate.",
        "Design a URL shortener like bit.ly",
        "You led a team. Walk me through your management style.",
        "What would you do if your manager gave you an impossible deadline?",
        "What is your expected salary?",
        "Why do you want to join our company?",
        "What is your greatest weakness?",
        "Explain the difference between SQL and NoSQL databases.",
    ]

    print("=== Intent Classifier Test ===")
    for q in test_questions:
        intent, conf, label = classify_intent(q)
        framework = get_response_framework(intent)
        print(f"\nQ: {q[:60]}")
        print(f"   -> {label} (confidence: {conf:.1%})")
        print(f"   Framework: {framework}")
