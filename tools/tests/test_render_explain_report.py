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
reader: 팀 리뷰어
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

- A) 코드가 짧아지기 때문에
- B) 피크 구간 경합을 줄이려고
- C) 테스트가 쉬워지기 때문에
- D) 로그가 줄어들기 때문에

### Q2. 발급 경합은 어디서 생겼나?

- A) 큐 선점 단계에서 생겼다
- B) 발급 시점 행 잠금에서
- C) 대기표 조회 단계에서다
- D) 입장 처리 단계에서였다

### Q3. 선점에 실패하면 어떻게 되나?

- A) 즉시 오류를 반환한다
- B) 대기표를 그대로 준다
- C) 재시도 경로로 넘어간다
- D) 큐를 새로 만들어 준다

### Q4. 지금 폴백이 없는 지점은?

- A) 큐 장애 상황이다
- B) 대기표 만료 처리다
- C) 입장 순서 계산이다
- D) 사용자 인증 단계다

### Q5. 이 변경의 목표 지표는?

- A) 발급 코드 줄 수다
- B) 로그 저장 용량이다
- C) 테스트 실행 시간이다
- D) 피크 구간 대기 시간이다

## 정답과 해설

| # | 정답 | 해설 |
|---|---|---|
| Q1 | B | 잠금 경합이 대기 시간의 주원인이었다 |
| Q2 | B | 무엇이 바뀌었나 표의 발급 묶음 |
| Q3 | C | 직관 다이어그램의 실패 분기 |
| Q4 | A | 남은 위험과 미해결 항목 |
| Q5 | D | 한 줄 섹션 |
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
        self.assertIn('<span class="chip"><b>reader</b>팀 리뷰어</span>', html)
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

    def test_rejects_option_length_bias(self):
        biased = COMPLETE_NOTE.replace(
            "- B) 피크 구간 경합을 줄이려고",
            "- B) 피크 구간에서 발급 요청이 몰릴 때 행 잠금 경합이 대기 시간을 지배하기 때문에",
        )
        result, output = self.run_renderer(biased)

        self.assertNotEqual(0, result.returncode)
        self.assertFalse(output.exists())
        self.assertIn("퀴즈 규칙 위반", result.stderr)
        self.assertIn("보기 길이 편차", result.stderr)

    def test_rejects_banned_option(self):
        banned = COMPLETE_NOTE.replace("- D) 로그가 줄어들기 때문에", "- D) 위 보기가 모두 맞다")
        result, output = self.run_renderer(banned)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("금지 보기 사용", result.stderr)

    def test_rejects_answer_key_bias(self):
        skewed = COMPLETE_NOTE.replace("| Q3 | C |", "| Q3 | B |").replace("| Q4 | A |", "| Q4 | B |")
        result, output = self.run_renderer(skewed)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("3연속", result.stderr)
        self.assertIn("쏠림", result.stderr)

    def test_rejects_wrong_question_count(self):
        trimmed = COMPLETE_NOTE.replace("### Q5. 이 변경의 목표 지표는?", "### 참고. 이 변경의 목표 지표는?")
        result, output = self.run_renderer(trimmed)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("퀴즈 문항 5개 필요", result.stderr)

    def test_rejects_note_without_reader(self):
        anonymous = COMPLETE_NOTE.replace("reader: 팀 리뷰어\n", "")
        result, output = self.run_renderer(anonymous)

        self.assertNotEqual(0, result.returncode)
        self.assertFalse(output.exists())
        self.assertIn("frontmatter reader 누락", result.stderr)

    def test_rejects_note_missing_required_sections(self):
        result, output = self.run_renderer("# 제목\n\n## 한 줄\n\n내용\n")

        self.assertNotEqual(0, result.returncode)
        self.assertFalse(output.exists())
        self.assertIn("필수 섹션 누락", result.stderr)
        self.assertIn("퀴즈", result.stderr)
        self.assertIn("무엇이 바뀌었나 또는 무엇을 알아냈나", result.stderr)


if __name__ == "__main__":
    unittest.main()
