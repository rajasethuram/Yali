"""
Practice Mode — mock interview engine.
YALI asks questions, generates aggressive follow-ups, tracks session.
"""
import json
import random
import time
import sys
from pathlib import Path
from typing import Optional, Callable

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MIND_MODEL, MEMORY_DIR
from modules.cognitive.intent_classifier import classify_intent, INTENT_DISPLAY
from modules.cognitive.resume_parser import load_profile

import anthropic

QUESTION_BANK = {
    "behavioral": [
        "Tell me about a time you handled a conflict with a teammate.",
        "Describe a situation where you had to meet an impossible deadline.",
        "What is your greatest professional achievement?",
        "Tell me about a time you failed and what you learned.",
        "Describe a time you had to influence someone without authority.",
        "Give me an example of when you showed leadership.",
        "Tell me about a time you had to learn something quickly.",
        "Describe a situation where you had to manage competing priorities.",
        "What is your biggest weakness? Give me a specific example.",
        "Tell me about a time you disagreed with your manager.",
        "Describe a time you turned a negative situation into a positive one.",
        "Tell me about a time you had to give difficult feedback.",
    ],
    "technical": [
        "Design a URL shortener like bit.ly. Walk me through your architecture.",
        "Explain the difference between SQL and NoSQL databases.",
        "How would you design a scalable notification system?",
        "What is the time complexity of quicksort? When would you avoid it?",
        "Explain how you would design a rate limiter.",
        "What is a deadlock? How do you prevent it?",
        "Design a distributed cache system.",
        "Explain REST vs GraphQL. When would you use each?",
        "How does a load balancer work?",
        "Explain SOLID principles with examples.",
        "How would you optimize a slow SQL query?",
        "Design Twitter's newsfeed system.",
    ],
    "leadership": [
        "Describe how you have led a team through a challenging project.",
        "How do you handle underperforming team members?",
        "Tell me about a time you had to make a difficult decision under uncertainty.",
        "How do you prioritize when everything is urgent?",
        "Describe your experience mentoring junior engineers.",
        "How do you handle stakeholder disagreements?",
    ],
    "situational": [
        "What would you do if you discovered a critical bug the day before launch?",
        "How would you handle it if your team missed a major deadline?",
        "What would you do if you were assigned to a project with unclear requirements?",
        "How would you approach joining a new team with low morale?",
        "What would you do if two senior engineers disagreed on architecture?",
    ],
    "company": [
        "Why do you want to work here?",
        "Where do you see yourself in 5 years?",
        "Why should we hire you over other candidates?",
        "What do you know about our company?",
        "What questions do you have for us?",
    ],
}

FOLLOWUP_SYSTEM = """You are a tough but fair interviewer conducting a mock interview.
The candidate just answered a question. Generate ONE aggressive follow-up question.
Follow-up should:
- Dig deeper into a specific claim they made
- Challenge their answer with a "but what if" scenario
- Ask for more specific numbers/metrics
- Question their decision-making
Keep it under 40 words. Be direct. No pleasantries."""


class PracticeSession:
    def __init__(self,
                 on_question: Optional[Callable[[str, str], None]] = None,
                 on_followup: Optional[Callable[[str], None]] = None,
                 on_session_end: Optional[Callable[[dict], None]] = None,
                 focus_areas: Optional[list] = None,
                 num_questions: int = 5):
        self.on_question = on_question or (lambda q, t: print(f"[QUESTION][{t}] {q}"))
        self.on_followup = on_followup or (lambda q: print(f"[FOLLOWUP] {q}"))
        self.on_session_end = on_session_end or (lambda s: print(f"[SESSION END] {json.dumps(s, indent=2)}"))
        self.focus_areas = focus_areas or ["behavioral", "technical", "situational"]
        self.num_questions = num_questions
        self.session_log = []
        self.start_time = None
        self._client = None

    def _get_client(self):
        if self._client is None and ANTHROPIC_API_KEY:
            self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._client

    def _pick_question(self, used_questions: set) -> tuple[str, str]:
        available = []
        for area in self.focus_areas:
            for q in QUESTION_BANK.get(area, []):
                if q not in used_questions:
                    available.append((q, area))

        if not available:
            for area in QUESTION_BANK:
                for q in QUESTION_BANK[area]:
                    if q not in used_questions:
                        available.append((q, area))

        if not available:
            return ("Tell me about yourself.", "behavioral")

        return random.choice(available)

    def _generate_followup(self, question: str, user_answer: str) -> str:
        client = self._get_client()
        if not client:
            followups = [
                "Can you give me a specific metric or number to back that up?",
                "What would you do differently if you faced that situation again?",
                "How did your team react to that decision?",
                "What was the biggest risk in that approach?",
                "If that approach had failed, what was your backup plan?",
            ]
            return random.choice(followups)

        try:
            response = client.messages.create(
                model=CLAUDE_MIND_MODEL,
                max_tokens=100,
                system=FOLLOWUP_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": f"Original question: {question}\n\nCandidate answer: {user_answer[:500]}"
                    }
                ],
            )
            return response.content[0].text.strip()
        except Exception:
            return "Can you elaborate with a specific example or metric?"

    def run_question(self, question: str, question_type: str, user_answer: str,
                     max_followups: int = 2) -> dict:
        entry = {
            "question": question,
            "type": question_type,
            "user_answer": user_answer,
            "followups": [],
            "timestamp": time.time(),
        }

        for i in range(max_followups):
            followup = self._generate_followup(question, user_answer)
            entry["followups"].append(followup)
            self.on_followup(followup)

            # In real usage, would capture user's follow-up answer via STT
            # For now, log the follow-up question
            if i < max_followups - 1:
                time.sleep(0.5)

        self.session_log.append(entry)
        return entry

    def start_session(self):
        self.start_time = time.time()
        used = set()
        print(f"[Practice] Starting session: {self.num_questions} questions, areas: {self.focus_areas}")

        for i in range(self.num_questions):
            question, q_type = self._pick_question(used)
            used.add(question)
            type_label = INTENT_DISPLAY.get(q_type, q_type)
            self.on_question(question, type_label)
            time.sleep(0.3)

        return self.get_session_summary()

    def get_session_summary(self) -> dict:
        duration = time.time() - (self.start_time or time.time())
        summary = {
            "total_questions": len(self.session_log),
            "duration_seconds": round(duration),
            "questions_by_type": {},
            "questions": self.session_log,
        }
        for entry in self.session_log:
            t = entry["type"]
            summary["questions_by_type"][t] = summary["questions_by_type"].get(t, 0) + 1

        self.on_session_end(summary)
        self._save_session(summary)
        return summary

    def _save_session(self, summary: dict):
        sessions_dir = MEMORY_DIR / "practice_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        fname = sessions_dir / f"session_{int(time.time())}.json"
        with open(fname, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[Practice] Session saved to {fname}")

    def get_question_list(self, areas: Optional[list] = None, count: int = 10) -> list[dict]:
        areas = areas or list(QUESTION_BANK.keys())
        result = []
        for area in areas:
            for q in QUESTION_BANK.get(area, []):
                result.append({"question": q, "type": area, "framework": ""})
        random.shuffle(result)
        return result[:count]


if __name__ == "__main__":
    def on_q(q, t):
        print(f"\n[{t}] {q}")

    def on_f(q):
        print(f"  Follow-up: {q}")

    session = PracticeSession(on_question=on_q, on_followup=on_f, num_questions=3)
    questions = session.get_question_list(count=3)
    print("=== Sample Practice Questions ===")
    for item in questions:
        print(f"[{item['type']}] {item['question']}")
