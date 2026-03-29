# YouTrack 티켓 가이드

> 전사 YouTrack 상태 플로우 기준 문서입니다.
> DEV2팀 스프린트 운영 규칙은 [docs/sprint/](../docs/sprint/) 를 참조합니다.

## DEV2팀 스프린트 운영 문서

| 문서 | 내용 |
|------|------|
| [티켓 작성 가이드](../docs/sprint/ticket-guide.md) | 5W1H 작성법, 스프린트 상태, 티켓 크기 기준 |
| [스토리 포인트 가이드](../docs/sprint/story-point-guide.md) | 직군별 SP 산정 기준 (1~13) |
| [스프린트 계획 운영 개요](../docs/sprint/sprint-planning-overview.md) | 맨데이 배분, 월간 타임라인 |
| [업무 계획 변경 절차](../docs/sprint/plan-change-process.md) | 긴급 요청·이월 처리 프로세스 |

---

## 티켓 상태 플로우

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   State                                      │
├──────────┬──────────────────────────────────────────────────────────────────┤
│          │                                                                   │
│ Backlog  │    ┌────────┐                                                    │
│          │    │  ToBe  │                                                    │
│          │    └───┬────┘                                                    │
├──────────┼────────┼─────────────────────────────────────────────────────────┤
│          │        │                                                          │
│ Planning │        ▼                                                          │
│          │    ┌───────────┐                                                  │
│          │    │ Submitted │                                                  │
│          │    └─────┬─────┘                                                  │
├──────────┼──────────┼───────────────────────────────────────────────────────┤
│          │          │                                                        │
│  ToDo    │          ▼                          ┌────────────┐               │
│          │    ┌────────┐                       │  Reopened  │◄──────────┐   │
│          │    │  Open  │◄──────────────────────┴─────┬──────┘           │   │
│          │    └───┬────┘                             │                  │   │
├──────────┼────────┼──────────────────────────────────┼──────────────────┼───┤
│          │        │                                  │                  │   │
│  Doing   │        ▼                                  │                  │   │
│          │    ┌─────────────┐                        │                  │   │
│          │    │ In Progress │◄───────────────────────┘                  │   │
│          │    └──────┬──────┘                                           │   │
├──────────┼───────────┼──────────────────────────────────────────────────┼───┤
│          │           │                                                  │   │
│   QA     │           ▼                                                  │   │
│          │       ┌────────┐                                             │   │
│          │       │ Fixed  │─────────────────────────────────────────────┘   │
│          │       └───┬────┘        (QA 실패 시 Reopened)                    │
├──────────┼───────────┼──────────────────────────────────────────────────────┤
│          │           │                                                       │
│  Done    │           ▼                                                       │
│          │    ┌──────────┐      ┌────────┐                                  │
│          │    │ Verified │      │ Closed │ ← (QA 통과 후)                   │
│          │    └──────────┘      └────────┘                                  │
├──────────┼──────────────────────────────────────────────────────────────────┤
│          │                                                                   │
│   Do     │  ┌───────────┐  ┌────────────────┐  ┌───────────┐               │
│   not    │  │ Won't fix │  │Can't Reproduce │  │ Duplicate │               │
│ changed  │  └───────────┘  └────────────────┘  └───────────┘               │
│          │  ┌────────────┐  ┌──────────┐                                    │
│          │  │ Incomplete │  │ Obsolete │                                    │
│          │  └────────────┘  └──────────┘                                    │
└──────────┴──────────────────────────────────────────────────────────────────┘
```

### Phase 요약

| Phase | 상태 | 설명 |
|-------|------|------|
| **Backlog** | ToBe | 논의 필요, 아이디어 뱅크 |
| **Planning** | Submitted | 기획 완료, 담당자 미배정 대기 |
| **ToDo** | Open, Reopened | 담당자 배정, 작업 예정 |
| **Doing** | In Progress | 작업 진행 중 |
| **QA** | Fixed | 개발 완료, QA 대기 |
| **Done** | Verified, Closed | 완료 |
| **Do not changed** | Won't fix, Can't Reproduce, Duplicate, Incomplete, Obsolete | 미처리 종료 |

### 상태별 상세 설명

#### 📋 Backlog
- SLA 수집 대상이 아닌 일정 없는 이슈
- 우선순위 낮은 이슈 보관용

#### 💡 ToBe
- 논의가 필요한 이슈 생성 시 사용
- 아이디어 뱅크 차원으로 자유롭게 생성 권장
- **요구사항**: [ToBe 이슈 요구사항](https://aladincommunication.youtrack.cloud/articles/CTO-A-4)

**ToBe → Submitted 전환 조건:**
1. 기획서 필요 시:
   - 하위 이슈로 "기획서 작성" 이슈 생성
   - Open → In Progress → Verified 로 진행
   - **소요시간 반드시 기록**
   - 기획서 완료 후 Submitted로 전환
2. 간단 이슈 시:
   - 이슈 내용에 설명 작성
   - 소요시간 기록 후 Submitted로 전환

#### 📬 Submitted
- 기획 완료, 담당자 미배정 대기 상태
- **요구사항**: [Submitted 이슈 요구사항](https://aladincommunication.youtrack.cloud/articles/CTO-A-5)
- 우선순위 설정 및 유형 재정의
- 참고: [우선순위 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-1)

#### 🟢 Open
- 담당팀/담당자 배정 완료, 작업 예정 상태
- **스펙 문서**: [개발 스펙 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-6)
- 관련 플랫폼, 서비스, CC, 관련팀 선택
- **예측 필드** 작성 필수

**이슈 분할 규칙:**
- 예측 2일 초과 시 → 자식 이슈로 분산
- 목표: 1일 이내 완료 가능한 단위로 분할

#### 🔄 Reopened
- 해결된 이슈가 재발생하거나 수정 불충분 시 사용
- Open과 동일하게 속성 수정

#### 🔵 In Progress
- 작업 진행 중 상태
- **매일 퇴근 전 소요시간 기록 필수**
- 참고: [소요시간 기록 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-3)

#### ✅ Fixed
- 개발 완료, QA 대기 상태

#### ✅ Verified
- 개발 없이 이슈 처리 완료 시 사용

#### ✅ Closed
- Fixed 후 QA 완료 시 사용

---

### 완료/보관 처리 상태

| 상태 | 사용 시점 |
|------|----------|
| **Won't fix** | 이슈 존재하나 해결 안 하기로 결정 |
| **Can't Reproduce** | 충분히 테스트했으나 재현 불가 |
| **Duplicate** | 다른 이슈와 중복 |
| **Incomplete** | 정보 부족으로 진행 불가, 더 이상 진행 불필요 |
| **Obsolete** | 시간 경과로 진행 불필요 |

---

## 주요 링크

- [ToBe 이슈 요구사항](https://aladincommunication.youtrack.cloud/articles/CTO-A-4)
- [Submitted 이슈 요구사항](https://aladincommunication.youtrack.cloud/articles/CTO-A-5)
- [우선순위 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-1)
- [소요시간 기록 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-3)
- [개발 스펙 가이드](https://aladincommunication.youtrack.cloud/articles/CTO-A-6)
