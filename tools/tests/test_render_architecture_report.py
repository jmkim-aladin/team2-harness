import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "render_architecture_report.py"


COMPLETE_REPORT = """---
type: analysis
title: 바자르 서버 전체 아키텍처 분석
canonical_id: analysis:bazaar/sample
status: draft
updated_at: 2026-07-10
service_id: bazaar
review_state: needs-review
evidence_level: E3
---

# 바자르 서버 전체 아키텍처 분석

## 결론

> 실용적 헥사고날 모듈러 모놀리스다.

## 분석 기준

- 브랜치: `feature/DEV2-6533`
- 커밋: `bf560a11`

## 아키텍처 맵

```text
apps -> usecase -> ports <- adapters
<script>alert("escaped")</script>
```

## 설계 철학

외부 연동 차이는 **Adapter** 안으로 격리한다.

## Clean·Hexagonal·DDD 평가

| 기준 | 평가 |
|---|---|
| 의존성 역전 | 잘 맞음 |

## 우선순위 발견

| 우선순위 | 문제 | 영향 |
|---|---|---|
| P0 | CI 테스트 제외 | 회귀 차단 실패 |
| P1 | Outbox 선점 경쟁 | 중복 발행 가능 |

## 네이밍과 구조

`executoor`를 `executor`로 고친다.

## 이어갈 원칙

1. Port와 Adapter 경계를 유지한다.
2. 외부 호출은 트랜잭션 밖에서 수행한다.

## 검증과 한계

- 메인 컴파일 성공
- 외부 DB는 호출하지 않음
"""


class RenderArchitectureReportTest(unittest.TestCase):
    def run_renderer(self, markdown: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        source = base / "report.md"
        output = base / "nested" / "report.html"
        source.write_text(markdown, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), str(output)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, output

    def test_renders_self_contained_reader_with_full_report_content(self):
        result, output = self.run_renderer(COMPLETE_REPORT)

        self.assertEqual(0, result.returncode, result.stderr)
        html = output.read_text(encoding="utf-8")
        self.assertIn('<html lang="ko">', html)
        self.assertIn("<title>바자르 서버 전체 아키텍처 분석</title>", html)
        self.assertIn('data-source-sha256="', html)
        self.assertIn('class="report-nav"', html)
        self.assertIn('href="#section-1"', html)
        self.assertIn("<table>", html)
        self.assertIn('class="priority p0"', html)
        self.assertIn('class="priority p1"', html)
        self.assertIn('&lt;script&gt;alert(&quot;escaped&quot;)&lt;/script&gt;', html)
        self.assertIn("@media print", html)
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertNotIn('<script src="http', html)
        self.assertNotIn('<link rel="stylesheet"', html)

    def test_rejects_report_missing_required_sections(self):
        result, output = self.run_renderer("# 제목\n\n## 결론\n\n내용\n")

        self.assertNotEqual(0, result.returncode)
        self.assertFalse(output.exists())
        self.assertIn("필수 섹션 누락", result.stderr)
        self.assertIn("분석 기준", result.stderr)


if __name__ == "__main__":
    unittest.main()
