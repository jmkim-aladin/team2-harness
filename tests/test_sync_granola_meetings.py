from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "sync_granola_meetings.py"
spec = importlib.util.spec_from_file_location("sync_granola_meetings", MODULE_PATH)
sync = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(sync)


class GranolaMeetingSyncTests(unittest.TestCase):
    def test_formats_granola_note_as_tolaría_meeting_note(self) -> None:
        note = {
            "id": "not_1d3tmYTlCICgjy",
            "title": "Project Sync / MAX API",
            "created_at": "2026-06-08T09:30:00Z",
            "updated_at": "2026-06-08T10:00:00Z",
            "web_url": "https://notes.granola.ai/d/example",
            "summary_markdown": "## Summary\n\n- Decided to split DEV2-1234.",
            "attendees": [
                {"name": "김정민", "email": "jmkim@aladin.co.kr"},
                {"name": "조은흠", "email": "heum2@aladin.co.kr"},
            ],
            "calendar_event": {
                "scheduled_start_time": "2026-06-08T09:30:00Z",
                "scheduled_end_time": "2026-06-08T10:00:00Z",
            },
        }

        rel_path, markdown = sync.render_meeting_note(note)

        self.assertEqual(rel_path, "wiki/processes/meetings/2026-06-08-project-sync-max-api.md")
        self.assertIn("type: meeting", markdown)
        self.assertIn("canonical_id: meeting:2026-06-08-project-sync-max-api", markdown)
        self.assertIn("granola_id: not_1d3tmYTlCICgjy", markdown)
        self.assertIn("source: granola", markdown)
        self.assertIn("# 2026-06-08 Project Sync / MAX API", markdown)
        self.assertIn("- 김정민 <jmkim@aladin.co.kr>", markdown)
        self.assertIn("## 요약", markdown)
        self.assertIn("- Decided to split DEV2-1234.", markdown)
        self.assertIn("## 결정", markdown)
        self.assertIn("## 후속 액션", markdown)

    def test_formats_with_korean_display_title_while_keeping_safe_filename(self) -> None:
        note = {
            "id": "not_1d3tmYTlCICgjy",
            "title": "Order and payment process review",
            "created_at": "2026-06-08T09:30:00Z",
            "updated_at": "2026-06-08T10:00:00Z",
            "summary_markdown": "- summary",
            "attendees": [],
            "calendar_event": {"scheduled_start_time": "2026-06-08T09:30:00Z"},
        }

        rel_path, markdown = sync.render_meeting_note(
            note,
            title_override="주문/결제 프로세스 검토",
        )

        self.assertEqual(
            rel_path,
            "wiki/processes/meetings/2026-06-08-order-and-payment-process-review.md",
        )
        self.assertIn('title: "2026-06-08 주문/결제 프로세스 검토"', markdown)
        self.assertIn("# 2026-06-08 주문/결제 프로세스 검토", markdown)

    def test_upserts_meeting_link_into_existing_daily_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            daily = vault / "wiki/processes/daily/2026-06-08.md"
            daily.parent.mkdir(parents=True)
            daily.write_text(
                "\n".join(
                    [
                        "---",
                        "type: daily",
                        "date: 2026-06-08",
                        "---",
                        "",
                        "# 2026-06-08",
                        "",
                        "## 오늘의 아젠다",
                        "",
                        "- [ ] DEV2-1234",
                        "",
                        "## 회의",
                        "",
                        "-",
                        "",
                        "## 메모",
                        "",
                        "-",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            changed = sync.upsert_daily_meeting_link(
                vault,
                "2026-06-08",
                "2026-06-08-project-sync-max-api",
                "Project Sync / MAX API",
                create_daily=False,
            )
            changed_again = sync.upsert_daily_meeting_link(
                vault,
                "2026-06-08",
                "2026-06-08-project-sync-max-api",
                "Project Sync / MAX API",
                create_daily=False,
            )

            text = daily.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertFalse(changed_again)
            self.assertEqual(text.count("[[2026-06-08-project-sync-max-api|Project Sync / MAX API]]"), 1)
            self.assertIn("## 회의\n\n- [[2026-06-08-project-sync-max-api|Project Sync / MAX API]]", text)

    def test_daily_link_is_skipped_when_daily_missing_and_create_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changed = sync.upsert_daily_meeting_link(
                Path(tmp),
                "2026-06-08",
                "2026-06-08-project-sync-max-api",
                "Project Sync / MAX API",
                create_daily=False,
            )

            self.assertFalse(changed)
            self.assertFalse((Path(tmp) / "wiki/processes/daily/2026-06-08.md").exists())

    def test_existing_meeting_note_preserves_manual_sections_when_granola_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            path = vault / "wiki/processes/meetings/2026-06-08-project-sync-max-api.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "\n".join(
                    [
                        "---",
                        "type: meeting",
                        "title: 2026-06-08 Project Sync / MAX API",
                        "canonical_id: meeting:2026-06-08-project-sync-max-api",
                        "status: canonical",
                        "updated_at: 2026-06-08",
                        "date: 2026-06-08",
                        "participants:",
                        "  - jmkim",
                        "related_tickets: []",
                        "related_services: []",
                        "source: granola",
                        "granola_id: not_1d3tmYTlCICgjy",
                        "---",
                        "",
                        "# 2026-06-08 Project Sync / MAX API",
                        "",
                        "<!-- generated:granola note_id=not_1d3tmYTlCICgjy updated=old -->",
                        "old summary",
                        "<!-- /generated -->",
                        "",
                        "## 결정",
                        "",
                        "- 수동으로 보강한 결정",
                        "",
                        "## 후속 액션",
                        "",
                        "- [ ] 수동 액션",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            note = {
                "id": "not_1d3tmYTlCICgjy",
                "title": "Project Sync / MAX API",
                "created_at": "2026-06-08T09:30:00Z",
                "updated_at": "2026-06-08T11:00:00Z",
                "web_url": "https://notes.granola.ai/d/example",
                "summary_markdown": "- new summary",
                "attendees": [],
                "calendar_event": {"scheduled_start_time": "2026-06-08T09:30:00Z"},
            }
            rel_path, markdown = sync.render_meeting_note(note)

            sync.upsert_meeting_note(vault, rel_path, markdown, note)

            text = path.read_text(encoding="utf-8")
            self.assertIn("- new summary", text)
            self.assertNotIn("old summary", text)
            self.assertIn("- 수동으로 보강한 결정", text)
            self.assertIn("- [ ] 수동 액션", text)

    def test_sync_uses_existing_file_with_same_granola_id_to_avoid_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            existing = vault / "wiki/processes/meetings/2026-06-08-korean-title.md"
            existing.parent.mkdir(parents=True)
            existing.write_text(
                "\n".join(
                    [
                        "---",
                        "type: meeting",
                        "title: 2026-06-08 한글 제목",
                        "canonical_id: meeting:2026-06-08-korean-title",
                        "status: canonical",
                        "updated_at: 2026-06-08",
                        "date: 2026-06-08",
                        "participants:",
                        "  - jmkim",
                        "related_tickets: []",
                        "related_services: []",
                        "source: granola",
                        "granola_id: not_1d3tmYTlCICgjy",
                        "---",
                        "",
                        "# 2026-06-08 한글 제목",
                        "",
                        "<!-- generated:granola note_id=not_1d3tmYTlCICgjy updated=old -->",
                        "old summary",
                        "<!-- /generated -->",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            note = {
                "id": "not_1d3tmYTlCICgjy",
                "title": "Order and payment process review",
                "created_at": "2026-06-08T09:30:00Z",
                "updated_at": "2026-06-08T11:00:00Z",
                "summary_markdown": "- new summary",
                "attendees": [],
                "calendar_event": {"scheduled_start_time": "2026-06-08T09:30:00Z"},
            }

            sync.sync_notes(
                [note],
                vault,
                include_transcript=False,
                create_daily=False,
                apply=True,
            )

            self.assertTrue(existing.exists())
            self.assertFalse(
                (
                    vault
                    / "wiki/processes/meetings/2026-06-08-order-and-payment-process-review.md"
                ).exists()
            )
            self.assertIn("- new summary", existing.read_text(encoding="utf-8"))

    def test_sync_updates_existing_display_title_and_daily_alias_from_title_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            meeting = vault / "wiki/processes/meetings/2026-06-08-order-and-payment-process-review.md"
            meeting.parent.mkdir(parents=True)
            meeting.write_text(
                "\n".join(
                    [
                        "---",
                        "type: meeting",
                        "title: 2026-06-08 Order and payment process review",
                        "canonical_id: meeting:2026-06-08-order-and-payment-process-review",
                        "status: canonical",
                        "updated_at: 2026-06-08",
                        "date: 2026-06-08",
                        "participants:",
                        "  - jmkim",
                        "related_tickets: []",
                        "related_services: []",
                        "source: granola",
                        "granola_id: not_1d3tmYTlCICgjy",
                        "---",
                        "",
                        "# 2026-06-08 Order and payment process review",
                        "",
                        "<!-- generated:granola note_id=not_1d3tmYTlCICgjy updated=old -->",
                        "old summary",
                        "<!-- /generated -->",
                        "",
                        "## 결정",
                        "",
                        "- 수동 결정",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            daily = vault / "wiki/processes/daily/2026-06-08.md"
            daily.parent.mkdir(parents=True)
            daily.write_text(
                "\n".join(
                    [
                        "---",
                        "type: daily",
                        "date: 2026-06-08",
                        "---",
                        "",
                        "# 2026-06-08",
                        "",
                        "## 회의",
                        "",
                        "- [[2026-06-08-order-and-payment-process-review|Order and payment process review]]",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            note = {
                "id": "not_1d3tmYTlCICgjy",
                "title": "Order and payment process review",
                "created_at": "2026-06-08T09:30:00Z",
                "updated_at": "2026-06-08T11:00:00Z",
                "summary_markdown": "- new summary",
                "attendees": [],
                "calendar_event": {"scheduled_start_time": "2026-06-08T09:30:00Z"},
            }

            sync.sync_notes(
                [note],
                vault,
                include_transcript=False,
                create_daily=False,
                apply=True,
                title_map={"not_1d3tmYTlCICgjy": "주문/결제 프로세스 검토"},
            )

            meeting_text = meeting.read_text(encoding="utf-8")
            daily_text = daily.read_text(encoding="utf-8")
            self.assertIn('title: "2026-06-08 주문/결제 프로세스 검토"', meeting_text)
            self.assertIn("# 2026-06-08 주문/결제 프로세스 검토", meeting_text)
            self.assertIn("- 수동 결정", meeting_text)
            self.assertIn("- new summary", meeting_text)
            self.assertIn(
                "[[2026-06-08-order-and-payment-process-review|주문/결제 프로세스 검토]]",
                daily_text,
            )
            self.assertNotIn("Order and payment process review", daily_text)


    def test_resolve_api_key_prefers_environment_then_keychain_reader(self) -> None:
        env = {"GRANOLA_API_KEY": "env-token"}

        self.assertEqual(
            sync.resolve_api_key(env, lambda: "keychain-token"),
            "env-token",
        )
        self.assertEqual(
            sync.resolve_api_key({}, lambda: "keychain-token"),
            "keychain-token",
        )

    def test_list_notes_passes_before_and_after_date_filters(self) -> None:
        class FakeClient(sync.GranolaClient):
            def __init__(self) -> None:
                super().__init__("token", "https://example.test")
                self.params_seen = []

            def request_json(self, path, params=None):
                self.params_seen.append(dict(params or {}))
                return {"notes": [], "hasMore": False, "cursor": None}

        client = FakeClient()

        client.list_notes(
            created_after="2026-05-01",
            created_before="2026-06-01",
            updated_after="2026-05-02",
            updated_before="2026-06-02",
            page_size=30,
        )

        self.assertEqual(
            client.params_seen[0],
            {
                "page_size": "30",
                "created_after": "2026-05-01",
                "created_before": "2026-06-01",
                "updated_after": "2026-05-02",
                "updated_before": "2026-06-02",
            },
        )


if __name__ == "__main__":
    unittest.main()
