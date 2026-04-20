"""
Speech Analyzer — analyzes transcripts and audio for quality metrics.
Measures: filler words, pace, hesitation, confidence score.
"""
import re
import json
import time
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MEMORY_DIR

FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "you know", "basically", "literally",
    "actually", "honestly", "kind of", "sort of", "i mean", "right",
    "so yeah", "and stuff", "whatever", "anyway", "i guess",
]

STRONG_WORDS = [
    "specifically", "demonstrated", "achieved", "delivered", "led", "built",
    "designed", "implemented", "improved", "increased", "reduced", "saved",
    "managed", "launched", "created", "developed", "optimized",
]

WEAK_WORDS = [
    "tried", "attempted", "hoped", "maybe", "possibly", "might", "could",
    "somewhat", "fairly", "quite", "rather", "perhaps",
]

IDEAL_WPM_MIN = 120
IDEAL_WPM_MAX = 160


class SpeechMetrics:
    def __init__(self):
        self.filler_count = 0
        self.filler_details = {}
        self.word_count = 0
        self.sentence_count = 0
        self.avg_sentence_length = 0
        self.wpm = 0
        self.duration_seconds = 0
        self.strong_word_count = 0
        self.weak_word_count = 0
        self.has_opening = False
        self.has_example = False
        self.has_numbers = False
        self.confidence_score = 0
        self.pace_score = 0
        self.clarity_score = 0
        self.structure_score = 0
        self.overall_score = 0
        self.suggestions = []

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def analyze_transcript(transcript: str, duration_seconds: float = 0) -> SpeechMetrics:
    metrics = SpeechMetrics()
    text = transcript.lower().strip()
    metrics.duration_seconds = duration_seconds

    # Word count
    words = re.findall(r'\b\w+\b', text)
    metrics.word_count = len(words)

    # WPM
    if duration_seconds > 0:
        metrics.wpm = round((metrics.word_count / duration_seconds) * 60)
    elif metrics.word_count > 0:
        # Estimate 120 wpm average
        metrics.wpm = 120

    # Sentence count
    sentences = re.split(r'[.!?]+', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]
    metrics.sentence_count = len(sentences)
    if metrics.sentence_count > 0:
        metrics.avg_sentence_length = round(metrics.word_count / metrics.sentence_count)

    # Filler word analysis
    for filler in FILLER_WORDS:
        pattern = r'\b' + re.escape(filler) + r'\b'
        count = len(re.findall(pattern, text))
        if count > 0:
            metrics.filler_details[filler] = count
            metrics.filler_count += count

    # Strong vs weak words
    for word in STRONG_WORDS:
        if re.search(r'\b' + word + r'\b', text):
            metrics.strong_word_count += 1

    for word in WEAK_WORDS:
        count = len(re.findall(r'\b' + word + r'\b', text))
        metrics.weak_word_count += count

    # Structure detection
    metrics.has_opening = any(
        text.startswith(w) for w in ["i ", "my ", "in my", "one of", "at my", "when i"]
    )
    metrics.has_example = any(
        phrase in text for phrase in [
            "for example", "for instance", "specifically", "at my",
            "in my previous", "one time", "when i was", "in one project"
        ]
    )
    metrics.has_numbers = bool(re.search(r'\b\d+[%x]?\b|\b\d+\s*(percent|times|users|engineers|million)', text))

    # Score calculations
    # Confidence score: based on filler density, strong/weak word ratio
    filler_density = metrics.filler_count / max(metrics.word_count, 1)
    filler_penalty = min(filler_density * 200, 40)
    weak_penalty = min(metrics.weak_word_count * 5, 20)
    strong_bonus = min(metrics.strong_word_count * 5, 20)
    metrics.confidence_score = max(0, min(100, int(80 - filler_penalty - weak_penalty + strong_bonus)))

    # Pace score
    if IDEAL_WPM_MIN <= metrics.wpm <= IDEAL_WPM_MAX:
        metrics.pace_score = 100
    elif metrics.wpm < IDEAL_WPM_MIN:
        metrics.pace_score = max(0, int(100 - (IDEAL_WPM_MIN - metrics.wpm) * 2))
    else:
        metrics.pace_score = max(0, int(100 - (metrics.wpm - IDEAL_WPM_MAX) * 1.5))

    # Clarity score: sentence length, structure
    len_score = 100 if 10 <= metrics.avg_sentence_length <= 20 else max(0, 100 - abs(15 - metrics.avg_sentence_length) * 5)
    metrics.clarity_score = int((len_score + metrics.confidence_score) / 2)

    # Structure score
    structure_points = 0
    if metrics.has_opening:
        structure_points += 30
    if metrics.has_example:
        structure_points += 35
    if metrics.has_numbers:
        structure_points += 20
    if metrics.sentence_count >= 3:
        structure_points += 15
    metrics.structure_score = structure_points

    # Overall score
    metrics.overall_score = int(
        metrics.confidence_score * 0.35 +
        metrics.pace_score * 0.25 +
        metrics.clarity_score * 0.20 +
        metrics.structure_score * 0.20
    )

    # Generate suggestions
    metrics.suggestions = _generate_suggestions(metrics)

    return metrics


def _generate_suggestions(m: SpeechMetrics) -> list[str]:
    suggestions = []

    if m.filler_count > 5:
        top_fillers = sorted(m.filler_details.items(), key=lambda x: x[1], reverse=True)[:3]
        filler_str = ", ".join(f'"{f}" ({c}x)' for f, c in top_fillers)
        suggestions.append(f"Reduce filler words: {filler_str}. Pause silently instead.")

    if m.wpm > IDEAL_WPM_MAX:
        suggestions.append(f"Slow down: you spoke at {m.wpm} wpm (ideal: {IDEAL_WPM_MIN}-{IDEAL_WPM_MAX}). Take deliberate pauses.")
    elif m.wpm < IDEAL_WPM_MIN and m.wpm > 0:
        suggestions.append(f"Pick up pace: {m.wpm} wpm is too slow (ideal: {IDEAL_WPM_MIN}-{IDEAL_WPM_MAX}).")

    if not m.has_example:
        suggestions.append("Add a specific example or story. Answers without examples score 30% lower.")

    if not m.has_numbers:
        suggestions.append("Include a number or metric (%, time saved, team size). Numbers = credibility.")

    if m.weak_word_count > 3:
        suggestions.append(f"Remove weak hedging words (tried/maybe/possibly). Use definitive language.")

    if m.avg_sentence_length > 25:
        suggestions.append("Shorten sentences. Aim for 10-20 words per sentence for clarity.")

    if m.structure_score < 50:
        suggestions.append("Use the STAR framework: Situation -> Task -> Action -> Result.")

    if m.confidence_score >= 85:
        suggestions.append("Strong confidence language! Keep this tone.")

    return suggestions


class ReviewEngine:
    def __init__(self):
        self.session_metrics = []

    def analyze_answer(self, transcript: str, question: str,
                       duration_seconds: float = 0) -> dict:
        metrics = analyze_transcript(transcript, duration_seconds)
        entry = {
            "question": question,
            "transcript": transcript,
            "duration": duration_seconds,
            "metrics": metrics.to_dict(),
            "timestamp": time.time(),
        }
        self.session_metrics.append(entry)
        return entry

    def get_session_report(self) -> dict:
        if not self.session_metrics:
            return {}

        avg_confidence = sum(e["metrics"]["confidence_score"] for e in self.session_metrics) / len(self.session_metrics)
        avg_pace = sum(e["metrics"]["pace_score"] for e in self.session_metrics) / len(self.session_metrics)
        avg_structure = sum(e["metrics"]["structure_score"] for e in self.session_metrics) / len(self.session_metrics)
        avg_overall = sum(e["metrics"]["overall_score"] for e in self.session_metrics) / len(self.session_metrics)
        total_fillers = sum(e["metrics"]["filler_count"] for e in self.session_metrics)

        all_suggestions = []
        for e in self.session_metrics:
            all_suggestions.extend(e["metrics"]["suggestions"])

        # Deduplicate suggestions, keep most common
        from collections import Counter
        suggestion_counts = Counter(all_suggestions)
        top_suggestions = [s for s, _ in suggestion_counts.most_common(5)]

        report = {
            "total_answers": len(self.session_metrics),
            "avg_confidence_score": round(avg_confidence),
            "avg_pace_score": round(avg_pace),
            "avg_structure_score": round(avg_structure),
            "avg_overall_score": round(avg_overall),
            "total_filler_words": total_fillers,
            "top_suggestions": top_suggestions,
            "grade": _score_to_grade(avg_overall),
            "per_answer": self.session_metrics,
        }

        self._save_report(report)
        return report

    def _save_report(self, report: dict):
        reports_dir = MEMORY_DIR / "review_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        fname = reports_dir / f"review_{int(time.time())}.json"
        with open(fname, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[Review] Report saved to {fname}")


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return "A+ (Interview-ready)"
    elif score >= 80:
        return "A (Strong)"
    elif score >= 70:
        return "B (Good, minor polish needed)"
    elif score >= 60:
        return "C (Needs practice)"
    else:
        return "D (Significant improvement needed)"


if __name__ == "__main__":
    sample = """
    So um I basically led a team of engineers and like we tried to implement a new system.
    Um so yeah the project was kind of successful I guess.
    We maybe improved the response time by like 30 percent or something.
    """

    sample_good = """
    At my previous company I led a team of 8 engineers to redesign our payment processing system.
    We identified the bottleneck in our database queries and implemented a caching layer using Redis.
    Specifically, I reduced API response time by 40% and cut server costs by $50K annually.
    The project was delivered on time and became the foundation for our new microservices architecture.
    """

    print("=== Speech Analyzer Test ===")
    print("\n--- Weak answer ---")
    m1 = analyze_transcript(sample, duration_seconds=20)
    print(f"Overall score: {m1.overall_score}/100 ({_score_to_grade(m1.overall_score)})")
    print(f"Filler words: {m1.filler_count} ({m1.filler_details})")
    print(f"Suggestions: {m1.suggestions[:2]}")

    print("\n--- Strong answer ---")
    m2 = analyze_transcript(sample_good, duration_seconds=25)
    print(f"Overall score: {m2.overall_score}/100 ({_score_to_grade(m2.overall_score)})")
    print(f"Filler words: {m2.filler_count}")
    print(f"Has numbers: {m2.has_numbers}, Has example: {m2.has_example}")
    print(f"Suggestions: {m2.suggestions[:2]}")
