from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "ticket_schedule.py"
spec = importlib.util.spec_from_file_location("ticket_schedule", MODULE_PATH)
ts = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ts)

TODAY = dt.date(2026, 10, 19)
REF = (2026, 10)
KST = dt.timezone(dt.timedelta(hours=9))
TAG_QUERY = "tag: 2610-planned Type: Feature State: Open, {In Progress}"


def ms(day: int, month: int = 10, hour: int = 9) -> int:
    """2026-{month}-{day} {hour}:00 KST → epoch ms."""
    return int(dt.datetime(2026, month, day, hour, tzinfo=KST).timestamp() * 1000)


def comment(day: int, text: str, *, month: int = 10, deleted: bool = False) -> dict:
    return {"text": text, "created": ms(day, month), "deleted": deleted}


def raw_issue(iid, *, type_="Feature", state="Open", children=(), resolved_children=(), comments=(),
              login="jm", name="김정민", description="", resolved=None, summary=None):
    """YouTrack /api/issues 응답 모양의 픽스처. children은 미해결, resolved_children은 해결된 하위."""
    return {
        "idReadable": iid,
        "summary": summary or f"{iid} 제목",
        "description": description,
        "resolved": resolved,
        "customFields": [
            {"name": "Type", "value": {"name": type_}},
            {"name": "State", "value": {"name": state}},
            {"name": "Assignee", "value": {"login": login, "name": name} if login else None},
        ],
        "links": [
            {"direction": "OUTWARD", "linkType": {"name": "Subtask"},
             "issues": [{"idReadable": c, "resolved": None} for c in children]
             + [{"idReadable": c, "resolved": ms(1)} for c in resolved_children]},
            {"direction": "INWARD", "linkType": {"name": "Subtask"}, "issues": []},
        ],
        "comments": list(comments),
    }


class FakeClient:
    """get/post만 흉내 낸다. 태그 질의는 planned 목록을, `issue id:` 질의는 해당 이슈를 돌려준다."""

    def __init__(self, issues, planned=()):
        self.issues = {i["idReadable"]: i for i in issues}
        self.planned = list(planned)
        self.gets = []
        self.posts = []

    def get(self, path, params):
        self.gets.append((path, dict(params)))
        if path == "/api/issues":
            query = params["query"]
            if query.startswith("tag:"):
                skip, top = int(params.get("$skip", 0)), int(params["$top"])
                return [self.issues[i] for i in self.planned][skip:skip + top]
            if query.startswith("issue id:"):
                ids = [s.strip() for s in query[len("issue id:"):].split(",")]
                return [self.issues[i] for i in ids if i in self.issues]
            raise AssertionError(f"예상 밖 질의: {query}")
        iid = path.split("/")[3]
        if iid not in self.issues:
            raise ts.YouTrackError(f"GET {path} → HTTP 404")
        return self.issues[iid]

    def post(self, path, params, body):
        self.posts.append((path, body))
        return {"id": f"c-{len(self.posts)}"}


def record(comments=(), description=""):
    return ts.normalize_issue(raw_issue("DEV2-1", comments=comments, description=description))


class LabelParsingTests(unittest.TestCase):
    def test_new_and_legacy_start_labels(self) -> None:
        cases = {
            "시작예정일: 2026-10-22": dt.date(2026, 10, 22),
            "예상 시작일: 2026-10-21": dt.date(2026, 10, 21),
            "예상 시작일 : 10월 19일": dt.date(2026, 10, 19),
            "예상 시작 일자: 11월 2일": dt.date(2026, 11, 2),
            "예상시작일：10월 23일": dt.date(2026, 10, 23),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(ts.label_dates(text, ts.KIND_START, REF), [expected])
                self.assertEqual(ts.label_dates(text, ts.KIND_DUE, REF), [])

    def test_new_and_legacy_due_labels(self) -> None:
        cases = {
            "완료목표일: 2026-10-30": dt.date(2026, 10, 30),
            "예상 종료일 : 10월 22일": dt.date(2026, 10, 22),
            "예상 완료일: 2026-11-04": dt.date(2026, 11, 4),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(ts.label_dates(text, ts.KIND_DUE, REF), [expected])
                self.assertEqual(ts.label_dates(text, ts.KIND_START, REF), [])

    def test_label_on_any_line_with_leading_space(self) -> None:
        text = "진행 공유드립니다.\n  예상 시작일 : 10월 19일\n예상 종료일 : 10월 22일"
        self.assertEqual(ts.label_dates(text, ts.KIND_START, REF), [dt.date(2026, 10, 19)])
        self.assertEqual(ts.label_dates(text, ts.KIND_DUE, REF), [dt.date(2026, 10, 22)])

    def test_sentence_form_and_other_date_formats_are_not_labels(self) -> None:
        for text in ("10월 3주차(19일~22일)에 작업 예정입니다.", "시작예정일: 10/22", "시작예정일 2026-10-22"):
            with self.subTest(text=text):
                self.assertEqual(ts.label_dates(text, ts.KIND_START, REF), [])

    def test_month_day_year_follows_target_month_with_six_month_wrap(self) -> None:
        self.assertEqual(ts.resolve_md(12, 30, (2026, 1)), dt.date(2025, 12, 30))
        self.assertEqual(ts.resolve_md(1, 5, (2026, 12)), dt.date(2027, 1, 5))
        self.assertEqual(ts.resolve_md(4, 1, (2026, 10)), dt.date(2026, 4, 1))  # 정확히 6개월은 보정하지 않음
        self.assertEqual(ts.resolve_md(3, 1, (2026, 10)), dt.date(2027, 3, 1))
        self.assertIsNone(ts.resolve_md(2, 30, REF))

    def test_invalid_iso_date_is_ignored(self) -> None:
        self.assertEqual(ts.label_dates("시작예정일: 2026-02-30", ts.KIND_START, REF), [])

    def test_most_recent_comment_wins_regardless_of_input_order(self) -> None:
        comments = [
            comment(16, "예상 시작일 : 10월 20일"),
            comment(3, "시작예정일: 2026-10-10"),
            comment(18, "완료목표일: 2026-10-31"),  # 다른 kind는 무시
        ]
        date, source = ts.latest_label(comments, ts.KIND_START, REF)
        self.assertEqual(date, dt.date(2026, 10, 20))
        self.assertEqual(source["created"], ms(16))


class StatusTests(unittest.TestCase):
    def test_ok_when_date_is_today_or_later(self) -> None:
        result = ts.classify(record([comment(10, "시작예정일: 2026-10-19")]), ts.KIND_START, REF, TODAY)
        self.assertEqual((result["status"], result["date"]), ("ok", "2026-10-19"))
        self.assertEqual(result["source"], {"created": "2026-10-10T09:00+09:00", "text": "시작예정일: 2026-10-19"})

    def test_overdue_when_date_passed(self) -> None:
        result = ts.classify(record([comment(10, "예상 종료일 : 10월 18일")]), ts.KIND_DUE, REF, TODAY)
        self.assertEqual((result["status"], result["date"]), ("overdue", "2026-10-18"))

    def test_unparsed_for_date_like_comments_without_needed_label(self) -> None:
        cases = [
            "10월 3주차(19일~22일)에 작업 예정입니다.",
            "10/22 착수 예정",
            "완료목표일: 2026-10-30",  # 반대 kind 라벨만 있음
            "다음 주 19일~ 진행",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = ts.classify(record([comment(10, text)]), ts.KIND_START, REF, TODAY)
                self.assertEqual(result["status"], "unparsed")
                self.assertIsNone(result["date"])
                self.assertIsNone(result["source"])
                self.assertEqual(len(result["hints"]), 1)

    def test_unscheduled_without_date_like_comments(self) -> None:
        rec = record([comment(10, "리뷰 요청드립니다."), comment(11, "1차 반영 완료", deleted=False)])
        result = ts.classify(rec, ts.KIND_START, REF, TODAY)
        self.assertEqual(result, {"date": None, "status": "unscheduled", "source": None, "hints": []})

    def test_deleted_comment_is_ignored(self) -> None:
        rec = record([comment(10, "시작예정일: 2026-10-22", deleted=True)])
        self.assertEqual(ts.classify(rec, ts.KIND_START, REF, TODAY)["status"], "unscheduled")

    def test_hints_are_latest_three_and_clipped(self) -> None:
        long_text = "10월 22일 " + "가" * 400
        comments = [comment(d, f"{d}일~ 진행") for d in (1, 2, 3)] + [comment(9, long_text)]
        result = ts.classify(record(comments), ts.KIND_START, REF, TODAY)
        self.assertEqual([h["created"][:10] for h in result["hints"]], ["2026-10-09", "2026-10-03", "2026-10-02"])
        self.assertEqual(len(result["hints"][0]["text"]), 300)


class WhenExtractTests(unittest.TestCase):
    def test_heading_section_until_next_heading(self) -> None:
        desc = "## What\n작업\n\n## When (언제 수행/발생하는가)\n- 10월 3주차 착수\n- 10월 말 완료\n\n## How\n방법"
        self.assertEqual(ts.extract_when(desc), "- 10월 3주차 착수\n- 10월 말 완료")

    def test_bold_and_inline_forms(self) -> None:
        self.assertEqual(ts.extract_when("**When(언제)**\n11월 오픈\n**How(어떻게)**\nx"), "11월 오픈")
        self.assertEqual(ts.extract_when("* **What** — 작업\n* **When** — 이후 순차 오픈.\n* **How** — x"),
                         "이후 순차 오픈.")

    def test_none_without_when_or_empty_body(self) -> None:
        self.assertIsNone(ts.extract_when("## What\n작업"))
        self.assertIsNone(ts.extract_when("### When\n\n### How\nx"))

    def test_clipped_to_400(self) -> None:
        self.assertEqual(len(ts.extract_when("## When\n" + "가" * 500)), 400)


def scan_fixture():
    """Open Feature 1(하위 무시) + 진행중 Feature 1(하위 Open·진행중·Backlog·해결) + 다른 담당자 Feature."""
    issues = [
        raw_issue("DEV2-10", state="Open", children=["DEV2-11"], comments=[comment(5, "시작예정일: 2026-10-22")],
                  description="## When\n10월 4주차 착수"),
        raw_issue("DEV2-11", type_="Task", state="Open"),
        raw_issue("DEV2-20", state="In Progress", children=["DEV2-23", "DEV2-21", "DEV2-22", "DEV2-24"],
                  resolved_children=["DEV2-25"], comments=[comment(5, "예상 종료일 : 10월 15일")]),
        raw_issue("DEV2-21", type_="Task", state="Open", login="eh", name="조은흠",
                  comments=[comment(12, "10월 3주차(19일~22일)에 작업 예정입니다.")]),
        raw_issue("DEV2-22", type_="Task", state="In Progress", comments=[comment(12, "완료목표일: 2026-10-24")]),
        raw_issue("DEV2-23", type_="Task", state="Backlog"),
        raw_issue("DEV2-24", type_="Task", state="Open"),
        raw_issue("DEV2-25", type_="Task", state="Fixed", resolved=ms(10)),
        raw_issue("DEV2-30", state="Open", login="eh", name="조은흠"),
        raw_issue("DEV2-40", state="Open", login=None),
    ]
    return FakeClient(issues, planned=["DEV2-40", "DEV2-30", "DEV2-20", "DEV2-10"])


class ScanTests(unittest.TestCase):
    def test_uses_contract_query(self) -> None:
        client = scan_fixture()
        ts.scan(client, "2610", TODAY)
        self.assertEqual(client.gets[0][1]["query"], TAG_QUERY)

    def test_expands_in_progress_feature_children_with_own_kind(self) -> None:
        result = ts.scan(scan_fixture(), "2610", TODAY)
        items = {it["id"]: it for it in result["items"]}
        self.assertNotIn("DEV2-11", items)  # Open Feature의 하위는 대상 아님
        self.assertNotIn("DEV2-23", items)  # Backlog 제외
        self.assertNotIn("DEV2-25", items)  # 해결된 하위 제외
        self.assertEqual({k: (items[k]["kind"], items[k]["label"], items[k]["parent"])
                          for k in ("DEV2-10", "DEV2-20", "DEV2-21", "DEV2-22", "DEV2-24")}, {
            "DEV2-10": ("start", "시작예정일", None),
            "DEV2-20": ("due", "완료목표일", None),
            "DEV2-21": ("start", "시작예정일", "DEV2-20"),
            "DEV2-22": ("due", "완료목표일", "DEV2-20"),
            "DEV2-24": ("start", "시작예정일", "DEV2-20"),
        })
        self.assertEqual(items["DEV2-10"]["when"], "10월 4주차 착수")
        self.assertEqual(items["DEV2-21"]["assignee"], {"login": "eh", "name": "조은흠"})

    def test_status_and_counts(self) -> None:
        result = ts.scan(scan_fixture(), "2610", TODAY)
        status = {it["id"]: it["status"] for it in result["items"]}
        self.assertEqual(status, {"DEV2-10": "ok", "DEV2-20": "overdue", "DEV2-21": "unparsed",
                                  "DEV2-22": "ok", "DEV2-24": "unscheduled", "DEV2-30": "unscheduled",
                                  "DEV2-40": "unscheduled"})
        self.assertEqual(result["counts"], {"ok": 2, "overdue": 1, "unparsed": 1, "unscheduled": 3})
        self.assertEqual((result["month"], result["tag"], result["today"]), ("2610", "2610-planned", "2026-10-19"))

    def test_sorted_by_assignee_then_feature_then_tasks(self) -> None:
        result = ts.scan(scan_fixture(), "2610", TODAY)
        self.assertEqual([it["id"] for it in result["items"]],
                         ["DEV2-10", "DEV2-20", "DEV2-22", "DEV2-24", "DEV2-21", "DEV2-30", "DEV2-40"])

    def test_assignee_filter_applies_per_item_after_expansion(self) -> None:
        result = ts.scan(scan_fixture(), "2610", TODAY, ["EH"])
        self.assertEqual([(it["id"], it["parent"]) for it in result["items"]],
                         [("DEV2-21", "DEV2-20"), ("DEV2-30", None)])
        self.assertEqual(result["counts"], {"ok": 0, "overdue": 0, "unparsed": 1, "unscheduled": 1})

    def test_task_under_two_features_listed_once(self) -> None:
        client = FakeClient([
            raw_issue("DEV2-1", state="In Progress", children=["DEV2-3"]),
            raw_issue("DEV2-2", state="In Progress", children=["DEV2-3"]),
            raw_issue("DEV2-3", type_="Task", state="Open"),
        ], planned=["DEV2-1", "DEV2-2"])
        items = ts.scan(client, "2610", TODAY)["items"]
        self.assertEqual([(it["id"], it["parent"]) for it in items],
                         [("DEV2-1", None), ("DEV2-3", "DEV2-1"), ("DEV2-2", None)])

    def test_pages_through_tag_query(self) -> None:
        issues = [raw_issue(f"DEV2-{n}") for n in range(1, ts.PAGE + 6)]
        client = FakeClient(issues, planned=[i["idReadable"] for i in issues])
        self.assertEqual(len(ts.scan(client, "2610", TODAY)["items"]), ts.PAGE + 5)
        self.assertEqual([p["$skip"] for _, p in client.gets], ["0", str(ts.PAGE)])

    def test_cli_rejects_bad_month_and_repo_output(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ts.main(["scan", "--month", "2613"], client=scan_fixture()), 2)
            self.assertEqual(ts.main(["scan", "--month", "2610", "--out", str(ts.REPO / "x.json")],
                                     client=scan_fixture()), 2)


def apply_fixture():
    return FakeClient([
        raw_issue("DEV2-1", state="Open"),
        raw_issue("DEV2-2", type_="Task", state="In Progress"),
        raw_issue("DEV2-3", state="Open"),  # 계획은 due인데 아직 Open
        raw_issue("DEV2-4", state="Fixed", resolved=ms(15)),
        raw_issue("DEV2-5", state="Open", comments=[comment(10, "시작예정일: 2026-10-22")]),
    ])


class ApplyTests(unittest.TestCase):
    def test_posts_exact_one_line_body(self) -> None:
        client = apply_fixture()
        results = ts.apply_plan(client, {"entries": [
            {"id": "DEV2-1", "kind": "start", "date": "2026-10-22"},
            {"id": "DEV2-2", "kind": "due", "date": "2026-10-30"},
        ]})
        self.assertEqual(client.posts, [
            ("/api/issues/DEV2-1/comments", {"text": "시작예정일: 2026-10-22"}),
            ("/api/issues/DEV2-2/comments", {"text": "완료목표일: 2026-10-30"}),
        ])
        self.assertEqual([(r["id"], r["result"], r["reason"]) for r in results],
                         [("DEV2-1", "posted", None), ("DEV2-2", "posted", None)])

    def test_skips_when_state_changed(self) -> None:
        client = apply_fixture()
        results = ts.apply_plan(client, {"entries": [
            {"id": "DEV2-3", "kind": "due", "date": "2026-10-30"},
            {"id": "DEV2-4", "kind": "start", "date": "2026-10-22"},
            {"id": "DEV2-1", "kind": "start", "date": "2026-10-23"},
        ]})
        self.assertEqual([(r["id"], r["result"], r["reason"]) for r in results], [
            ("DEV2-3", "skipped", "state_changed"),
            ("DEV2-4", "skipped", "state_changed"),
            ("DEV2-1", "posted", None),
        ])
        self.assertEqual([p for p, _ in client.posts], ["/api/issues/DEV2-1/comments"])

    def test_skips_when_same_date_already_latest(self) -> None:
        client = apply_fixture()
        results = ts.apply_plan(client, {"entries": [
            {"id": "DEV2-5", "kind": "start", "date": "2026-10-22"},
            {"id": "DEV2-5", "kind": "start", "date": "2026-10-26"},
        ]})
        self.assertEqual([(r["result"], r["reason"]) for r in results],
                         [("skipped", "already_set"), ("posted", None)])

    def test_invalid_entries_error_without_network(self) -> None:
        client = apply_fixture()
        results = ts.apply_plan(client, {"entries": [
            {"id": "DEV2-1", "kind": "begin", "date": "2026-10-22"},
            {"id": "DEV2-1", "kind": "start", "date": "10월 22일"},
            {"id": "DEV2-1", "kind": "start", "date": "2026-02-30"},
            {"id": "dev2 1", "kind": "start", "date": "2026-10-22"},
            "DEV2-1",
        ]})
        self.assertEqual([r["reason"] for r in results],
                         ["invalid_kind", "invalid_date", "invalid_date", "invalid_id", "invalid_entry"])
        self.assertTrue(all(r["result"] == "error" for r in results))
        self.assertEqual((client.gets, client.posts), ([], []))

    def test_lookup_error_does_not_stop_rest(self) -> None:
        client = apply_fixture()
        results = ts.apply_plan(client, {"entries": [
            {"id": "DEV2-999", "kind": "start", "date": "2026-10-22"},
            {"id": "DEV2-1", "kind": "start", "date": "2026-10-22"},
        ]})
        self.assertEqual([r["result"] for r in results], ["error", "posted"])

    def test_dry_run_cli_prints_bodies_without_post(self) -> None:
        client = apply_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            plan.write_text(json.dumps({"entries": [
                {"id": "DEV2-1", "kind": "start", "date": "2026-10-22"},
                {"id": "DEV2-3", "kind": "due", "date": "2026-10-30"},
            ]}), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ts.main(["apply", "--plan", str(plan), "--dry-run"], client=client)
        self.assertEqual(code, 0)
        self.assertEqual(client.posts, [])
        results = json.loads(out.getvalue())
        self.assertEqual([(r["id"], r["result"], r.get("body")) for r in results], [
            ("DEV2-1", "dry_run", "시작예정일: 2026-10-22"),
            ("DEV2-3", "skipped", None),
        ])

    def test_cli_rejects_malformed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            plan.write_text('[{"id": "DEV2-1"}]', encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ts.main(["apply", "--plan", str(plan)], client=apply_fixture()), 2)


if __name__ == "__main__":
    unittest.main()
