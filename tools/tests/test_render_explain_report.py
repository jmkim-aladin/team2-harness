import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "render_explain_report.py"


COMPLETE_NOTE = """---
type: explain
title: 대기표 발급 경로 변경 설명
mode: diff
subject: caravan feature/DEV2-6601
base: main
updated_at: 2026-08-03
summary: 대기표 발급을 큐 선점 방식으로 바꾼 이유와 영향을 설명한다.
---

# 대기표 발급 경로 변경 설명

## 한 줄

발급 시점의 DB 잠금을 큐 선점으로 바꿔 피크 구간 대기 시간을 줄였다.

## 배경

### 이 도메인을 처음 본다면

대기표는 입장 순서를 보장하는 토큰이다.

### 이 변경에 한정하면

기존 경로는 발급마다 행 잠금을 잡았다.

## 직관

```mermaid
flowchart TD
    A["요청 도착"] --> B{"큐 선점 성공"}
    B -->|성공| C["대기표 발급"]
    B -->|실패| D["재시도"]
```

토이 데이터로 보면 동시 요청 3건 중 1건만 잠금을 얻는다.

## 무엇이 바뀌었나

| 묶음 | 변경 | 이유 |
|---|---|---|
| 발급 | 잠금 제거 | 경합 감소 |

```kotlin
val ticket = queue.claim(userId)
<script>alert("escaped")</script>
```

## 남은 위험과 미해결

- 큐 장애 시 폴백 경로가 없다.

## 퀴즈

### Q1. 잠금을 제거한 이유는?

- A) 코드가 짧아져서
- B) 피크 구간 경합을 줄이려고
- C) 테스트가 쉬워져서
- D) 로그가 줄어서

## 정답과 해설

| # | 정답 | 해설 |
|---|---|---|
| Q1 | B | 잠금 경합이 대기 시간의 주원인이었다 |
"""


class RenderExplainReportTest(unittest.TestCase):
    def run_renderer(self, markdown: str, *flags: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source = base / "explain.md"
        output = base / "nested" / "explain.html"
        source.write_text(markdown, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), str(output), *flags],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def test_renders_reader_with_mermaid_and_collapsed_answers(self):
        result, output = self.run_renderer(COMPLETE_NOTE)

        self.assertEqual(0, result.returncode, result.stderr)
        html = output.read_text(encoding="utf-8")
        self.assertIn('<html lang="ko">', html)
        self.assertIn("<title>대기표 발급 경로 변경 설명</title>", html)
        self.assertIn('<pre class="mermaid">', html)
        self.assertIn('data-diagrams="1"', html)
        self.assertIn("cdn.jsdelivr.net/npm/mermaid", html)
        self.assertIn('<details class="answers">', html)
        self.assertIn("정답과 해설 보기", html)
        self.assertIn('<span class="chip"><b>mode</b>diff</span>', html)
        self.assertIn("<table>", html)
        self.assertIn('&lt;script&gt;alert(&quot;escaped&quot;)&lt;/script&gt;', html)
        self.assertIn("prefers-color-scheme: dark", html)

    def test_answers_stay_inside_their_own_section(self):
        result, output = self.run_renderer(COMPLETE_NOTE)

        self.assertEqual(0, result.returncode, result.stderr)
        html = output.read_text(encoding="utf-8")
        answers_start = html.index('<details class="answers">')
        quiz_start = html.index("Q1. 잠금을 제거한 이유는?")
        self.assertLess(quiz_start, answers_start)
        self.assertEqual(1, html.count("<details"))

    def test_no_mermaid_flag_keeps_output_offline_safe(self):
        result, output = self.run_renderer(COMPLETE_NOTE, "--no-mermaid")

        self.assertEqual(0, result.returncode, result.stderr)
        html = output.read_text(encoding="utf-8")
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertNotIn('<pre class="mermaid">', html)
        self.assertIn('class="language-mermaid"', html)

    def test_rejects_note_missing_required_sections(self):
        result, output = self.run_renderer("# 제목\n\n## 한 줄\n\n내용\n")

        self.assertNotEqual(0, result.returncode)
        self.assertFalse(output.exists())
        self.assertIn("필수 섹션 누락", result.stderr)
        self.assertIn("퀴즈", result.stderr)
        self.assertIn("무엇이 바뀌었나 또는 무엇을 알아냈나", result.stderr)


if __name__ == "__main__":
    unittest.main()
