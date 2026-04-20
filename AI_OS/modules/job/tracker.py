"""
Application Tracker — SQLite-based job application tracker.
Tracks status, follow-ups, responses. Powers HUD dashboard table.
"""
import sqlite3
import json
import time
import sys
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import JOBS_DB_PATH, MEMORY_DIR

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

STATUSES = ["applied", "viewed", "phone_screen", "interview", "offer", "rejected", "withdrawn"]


class ApplicationTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or JOBS_DB_PATH
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    job_id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT,
                    apply_url TEXT,
                    applied_date TEXT,
                    status TEXT DEFAULT 'applied',
                    match_score REAL DEFAULT 0,
                    follow_up_count INTEGER DEFAULT 0,
                    last_follow_up_date TEXT,
                    response_date TEXT,
                    notes TEXT,
                    resume_path TEXT,
                    cover_letter_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS follow_ups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    sent_date TEXT,
                    email_body TEXT,
                    FOREIGN KEY (job_id) REFERENCES applications(job_id)
                )
            """)

    def add_application(self, job_id: str, company: str, title: str,
                        source: str = "", apply_url: str = "",
                        match_score: float = 0,
                        resume_path: str = "", cover_letter_path: str = "") -> bool:
        today = time.strftime("%Y-%m-%d")
        with self._conn() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO applications
                    (job_id, company, title, source, apply_url, applied_date,
                     status, match_score, resume_path, cover_letter_path, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'applied', ?, ?, ?, ?)
                """, (job_id, company, title, source, apply_url, today,
                      match_score, resume_path, cover_letter_path, today))
                print(f"[Tracker] Added: {title} at {company}")
                return True
            except Exception as e:
                print(f"[Tracker] Error adding: {e}")
                return False

    def update_status(self, job_id: str, status: str, notes: str = "") -> bool:
        if status not in STATUSES:
            print(f"[Tracker] Invalid status: {status}. Valid: {STATUSES}")
            return False
        today = time.strftime("%Y-%m-%d")
        with self._conn() as conn:
            conn.execute("""
                UPDATE applications
                SET status=?, notes=COALESCE(NULLIF(?,''), notes),
                    updated_at=?,
                    response_date=CASE WHEN ? IN ('offer','rejected','phone_screen','interview')
                                  THEN ? ELSE response_date END
                WHERE job_id=?
            """, (status, notes, today, status, today, job_id))
        print(f"[Tracker] Updated {job_id}: {status}")
        return True

    def log_follow_up(self, job_id: str, email_body: str = "") -> bool:
        today = time.strftime("%Y-%m-%d")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO follow_ups (job_id, sent_date, email_body)
                VALUES (?, ?, ?)
            """, (job_id, today, email_body))
            conn.execute("""
                UPDATE applications
                SET follow_up_count = follow_up_count + 1,
                    last_follow_up_date = ?,
                    updated_at = ?
                WHERE job_id = ?
            """, (today, today, job_id))
        print(f"[Tracker] Follow-up logged for {job_id}")
        return True

    def get_all(self, status: Optional[str] = None) -> list[dict]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM applications WHERE status=? ORDER BY applied_date DESC",
                    (status,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM applications ORDER BY applied_date DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_pending_follow_ups(self, days_without_response: int = 7) -> list[dict]:
        """Get applications with no response after N days."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM applications
                WHERE status = 'applied'
                AND follow_up_count < 2
                AND julianday('now') - julianday(applied_date) >= ?
                AND (last_follow_up_date IS NULL
                     OR julianday('now') - julianday(last_follow_up_date) >= 7)
                ORDER BY applied_date ASC
            """, (days_without_response,)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            by_status = {}
            for row in conn.execute(
                "SELECT status, COUNT(*) as cnt FROM applications GROUP BY status"
            ).fetchall():
                by_status[row[0]] = row[1]

            recent_7d = conn.execute("""
                SELECT COUNT(*) FROM applications
                WHERE julianday('now') - julianday(applied_date) <= 7
            """).fetchone()[0]

        return {
            "total": total,
            "by_status": by_status,
            "applied_last_7_days": recent_7d,
            "interview_rate": round(
                (by_status.get("interview", 0) + by_status.get("phone_screen", 0))
                / max(total, 1) * 100, 1
            ),
        }

    def search(self, query: str) -> list[dict]:
        q = f"%{query}%"
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM applications
                WHERE company LIKE ? OR title LIKE ? OR notes LIKE ?
                ORDER BY applied_date DESC
            """, (q, q, q)).fetchall()
        return [dict(r) for r in rows]

    def export_csv(self, output_path: Optional[Path] = None) -> Path:
        import csv
        output_path = output_path or (MEMORY_DIR / f"applications_{time.strftime('%Y%m%d')}.csv")
        apps = self.get_all()
        if not apps:
            print("[Tracker] No applications to export")
            return output_path
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=apps[0].keys())
            writer.writeheader()
            writer.writerows(apps)
        print(f"[Tracker] Exported {len(apps)} applications to {output_path}")
        return output_path

    def delete_application(self, job_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM applications WHERE job_id=?", (job_id,))
        print(f"[Tracker] Deleted {job_id}")
        return True


# Singleton instance
_tracker: Optional[ApplicationTracker] = None

def get_tracker() -> ApplicationTracker:
    global _tracker
    if _tracker is None:
        _tracker = ApplicationTracker()
    return _tracker


if __name__ == "__main__":
    t = ApplicationTracker()

    # Test data
    t.add_application("test_001", "Google", "Senior Python Engineer", "linkedin",
                      "https://linkedin.com/jobs/123", match_score=87)
    t.add_application("test_002", "Flipkart", "Backend Developer", "indeed",
                      "https://indeed.com/jobs/456", match_score=74)
    t.add_application("test_003", "Swiggy", "Software Engineer", "naukri",
                      "https://naukri.com/789", match_score=68)

    t.update_status("test_002", "phone_screen", "HR called — scheduled for Wednesday")

    stats = t.get_stats()
    print("\n=== Application Stats ===")
    print(f"Total: {stats['total']}")
    print(f"By status: {stats['by_status']}")
    print(f"Last 7 days: {stats['applied_last_7_days']}")
    print(f"Interview rate: {stats['interview_rate']}%")

    print("\n=== All Applications ===")
    for app in t.get_all():
        print(f"  [{app['status']}] {app['title']} @ {app['company']} (score: {app['match_score']})")
