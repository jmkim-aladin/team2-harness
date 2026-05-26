# 운영 위키 문서 언어와 제목 정책

## 목적

Obsidian vault(운영·도메인 지식 SSOT)와 팀 하네스 문서가 서비스별로 바로 구분되고, 한국어 사용자가 검색/검토하기 쉬운 형태로 유지되도록 문서 언어와 제목 기준을 고정한다. 저장소 경계 정의는 [knowledge-base-policy.md](./knowledge-base-policy.md) 참조.

## 적용 범위

- 팀 하네스의 `docs/`, `policies/`, `templates/`
- Obsidian vault의 `wiki/`, `registry/`, `imports/` 등 운영업무·도메인 지식 트리
- Ralph Loop, Graphify sidecar, DB 이관/CDC 진단, 레거시 현대화/DB 분리 분석 산출물
- 자동 생성 인덱스, Queue, Register, Querybook 문서

## 기본 원칙

- 파일명과 Obsidian 링크 target slug는 영어를 허용한다. 파일명은 기계 식별자이므로 한글화 대상이 아니다.
- 모든 문서 내용은 한국어로 작성한다. 여기서 내용은 frontmatter `title`, H1/H2/H3 등 섹션 제목, 본문, 목록, 표의 사람이 읽는 셀, wikilink 표시명을 포함한다.
- 코드, 식별자, API, SP, Table, CDC, DTO, Querybook, Graphify처럼 의미가 고정된 기술 용어는 영어를 허용한다.
- API/SP/Table/Column/Class/Method/File path/CSV column 같은 기술 식별자는 원문 영어를 보존한다. 단, 식별자를 설명하는 문장은 한국어로 쓴다.
- `Command`, `Querybook`, `Shadow-Read`, `Reconciliation`, `Adapter`, `Read Model`, `CDC`, `Graphify`, `Owner`, `Runtime`, `Source Gap`처럼 분석/운영 문맥에서 통용되는 기술 용어는 무리하게 번역하지 않는다.
- 한글화의 목적은 모든 단어를 한국어로 바꾸는 것이 아니라, 문서가 한국어 독자에게 도메인 판단, 운영 기준, 이관 위험, 후속 조치를 이해할 수 있게 기술되는 것이다.
- 영어 기술 용어만으로 문서 제목을 만들지 않는다. 제목은 한국어 문장 또는 한국어 명사구가 중심이어야 한다.
- 파일명은 기존 규칙대로 `kebab-case.md`를 사용하며, 서비스 식별을 위해 `service_id` 접두어를 유지한다.
- H1 제목과 Obsidian `title` frontmatter는 사람이 읽는 이름이므로 서비스의 한글 표시명으로 시작한다.

## 서비스 제목 접두어

서비스별 문서의 H1 제목과 `title` frontmatter는 아래 접두어로 시작한다.

| service_id | 제목 접두어 | 예시 |
|---|---|---|
| `tobe` | `투비` | `투비 주문/정산 CDC 후보` |
| `web-aladin`, `aladin` | `알라딘 웹` | `알라딘 웹 주문 Raw SQL 쓰기 경계` |
| `aladin-infra` | `알라딘 인프라` | `알라딘 인프라 WebCatalog SP 경계` |
| `max` | `만권당` | `만권당 결제 정산 경계` |
| `naru` | `나루` | `나루 인증 계약` |
| `bazaar` | `바자르` | `바자르 상품 이벤트 경계` |
| `aasm` | `AASM` | `AASM 설정 운영 가이드` |
| `b2b-store`, `storefront` | `스토어프론트` | `스토어프론트 테넌트 계약` |

공통 문서는 `공통`, `DEV2`, `운영 위키`, `DB 이관`, `레거시 현대화`처럼 범위를 먼저 드러내는 한국어 접두어를 사용한다.

## 파일명과 제목 분리

파일명은 기계가 안정적으로 찾기 위한 이름이고, H1 제목은 사람이 탐색하기 위한 이름이다.

| 항목 | 규칙 | 예시 |
|---|---|---|
| 파일명 | `service_id` + 영문 kebab-case | vault `wiki/inventory/tobe-sp-inventory.md` |
| H1/title | 한글 서비스명 + 한국어 제목 | `# 투비 SP 인벤토리` |
| 링크 표시명 | H1과 같은 한국어 이름 권장 | `[[tobe-sp-inventory|투비 SP 인벤토리]]` |

파일명과 링크 target은 영어여도 되지만, 사람이 화면에서 읽는 표시명은 한국어여야 한다.

| 허용 | 피할 표현 |
|---|---|
| `[[tobe-sp-inventory|투비 SP 인벤토리]]` | `[[tobe-sp-inventory|Tobe SP Inventory]]` |
| `- 투비 서비스 시작은 \`Tobe_ServiceStart\` SP 계약을 유지한다.` | `- StartService calls Tobe_ServiceStart.` |
| `| CDC 등급 | 판단 근거 |` | `| CDC Grade | Rationale |` |

## 제목 예시

| 피할 제목 | 사용할 제목 |
|---|---|
| `Tobe SP Inventory` | `투비 SP 인벤토리` |
| `Web-Aladin Raw SQL Write Boundary` | `알라딘 웹 Raw SQL 쓰기 경계` |
| `Discovery Queue` | `운영 위키 발견 큐` |
| `Action Register` | `운영 위키 조치 등록부` |
| `Missing SP Source Evidence Import Workspace` | `Missing SP Source 근거 Import 작업 공간` |
| `Tobe Account Read Service-Start Shadow-Read Querybook` | `투비 계정 읽기 Service-Start Shadow-Read Querybook` |

## 생성 산출물 작성 기준

새 문서를 만들 때는 다음을 동시에 맞춘다.

- 파일명: `service_id` 접두어와 `kebab-case.md`
- H1: 서비스별 한글 접두어로 시작
- frontmatter `title`: H1과 동일하거나 같은 한국어 제목
- `service` 또는 `service_id`: 기계 판별용 값 유지
- `Related Links` generated block: 기존 생성기 규칙 유지

## 기존 문서 보정 기준

기존 영어 제목 문서는 대량 수동 수정하지 않는다. 아래 순서로 배치 보정한다.

1. 현재 H1/title과 파일명을 inventory로 뽑는다.
2. 서비스별 접두어 매핑으로 변경 후보를 만든다.
3. wikilink 표시명, generated block, index 영향 범위를 확인한다.
4. 파일명 변경이 필요한 경우와 H1/title만 바꿀 경우를 분리한다.
5. 로컬 Obsidian에서 `python3 scripts/generate_wiki.py`와 `python3 scripts/lint_wiki.py`를 실행한다.
6. 검증 전에는 canonical 문서 제목 정비 완료로 표시하지 않는다.

## 금지 사항

- 영어 제목을 그대로 새 문서의 H1으로 사용하는 것
- 한국어 설명 없이 영어 문장만으로 도메인 판단, 운영 기준, 위험, 후속 조치를 남기는 것
- 폴더 구조만 믿고 H1에서 서비스명을 생략하는 것
- `Tobe`, `Web-Aladin` 같은 영문 서비스명을 사람용 제목 접두어로 쓰는 것
- 기존 문서의 파일명을 한 번에 바꾸고 링크 검증을 생략하는 것
