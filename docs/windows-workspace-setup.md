# Windows workspace 셋업

Windows에서도 macOS와 같은 팀 하네스, 위키, 서비스 레포 구성을 쓰기 위한 절차입니다.

## 현재 기준 경로

- workspace: `C:\Users\jmkim\Documents\workspace`
- team2 harness: `C:\Users\jmkim\Documents\workspace\team2-harness`
- wiki: `C:\Users\jmkim\Documents\workspace\wiki`
- 서비스 레포: `C:\Users\jmkim\Documents\workspace\<group>\<repo-name>`

## workspace 묶음

| 묶음 | 경로 |
|------|------|
| max | `C:\Users\jmkim\Documents\workspace\max\*` |
| tobe | `C:\Users\jmkim\Documents\workspace\tobe\*` |
| shopping | `C:\Users\jmkim\Documents\workspace\shopping\*` |
| ebook | `C:\Users\jmkim\Documents\workspace\ebook\*` |
| naru | `C:\Users\jmkim\Documents\workspace\naru\NaruServer` |
| bazaar | `C:\Users\jmkim\Documents\workspace\bazaar\BazaarServer` |
| aasm | `C:\Users\jmkim\Documents\workspace\s3manager` |

## 1회 셋업

PowerShell에서 실행합니다.

```powershell
cd C:\Users\jmkim\Documents\workspace\team2-harness
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -CloneRepos
```

스크립트가 수행하는 일:

1. `TEAM2_HARNESS_PATH`, `TEAM2_WORKSPACE_PATH`, `YOUTRACK_BASE_URL` 사용자 환경변수 설정
2. `~\.claude\settings.json`에 같은 값 등록
3. `~\.claude\commands\ad`를 하네스의 `.claude\commands\ad`로 연결
4. `catalog/*.yaml`의 GitHub 레포를 workspace 묶음 경로 하위에 클론
5. Windows에서 checkout 불가능한 일부 경로가 있는 레포는 sparse checkout으로 문제 파일만 제외

이미 클론된 레포는 삭제하거나 덮어쓰지 않고 `core.longpaths=true` 같은 Windows용 Git 옵션만 보강합니다.

사용자 환경변수는 새 터미널과 새 앱 세션부터 자동 반영됩니다.

## 레포만 다시 동기화

하네스 카탈로그에 레포가 추가되었을 때는 아래 명령만 다시 실행합니다.

```powershell
cd C:\Users\jmkim\Documents\workspace\team2-harness
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\clone-catalog-repos.ps1
```

## Windows checkout 예외

다음 레포는 히스토리에 Windows 파일시스템에서 허용하지 않는 경로가 있어 sparse checkout 예외를 적용합니다.

- `Ebook_Web_Viewer`: literal backslash가 포함된 `logs\...` 경로 제외
- `EbookIos`: `:`가 포함된 HTML 리소스 1개 제외

이 예외는 Windows 작업 트리를 깨끗하게 유지하기 위한 것이며, Git 오브젝트와 원격 히스토리는 그대로 유지됩니다. 해당 파일을 실제로 수정해야 하는 경우 macOS 환경에서 작업합니다.

## wiki 참조 shopping 레포

워크플로우 문서에서 직접 참조하는 shopping 레포도 같은 묶음에 둡니다.

- `C:\Users\jmkim\Documents\workspace\shopping\dev1-web-aladin`
- `C:\Users\jmkim\Documents\workspace\shopping\mall-search`

`shop-db-script`는 위키에 경로가 남아 있지만 현재 `https://github.com/AladinCommunication/shop-db-script` 원격을 찾을 수 없어 자동 클론 대상에서 제외했습니다.

## macOS와 Windows 공통 운영 원칙

- 하네스 정책과 스킬은 `TEAM2_HARNESS_PATH`를 기준으로 참조합니다.
- 서비스 작업은 각 서비스 레포에서 실행합니다.
- 하네스/정책/워크플로우 수정은 `team2-harness`에서 관리합니다.
- 위키 자료는 workspace의 `wiki` 레포를 기준으로 동기화합니다.
