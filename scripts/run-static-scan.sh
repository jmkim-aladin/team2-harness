#!/usr/bin/env bash
#
# run-static-scan.sh — 개발 2팀 정적 점검 원커맨드 러너 (P1)
#
# SonarQube + Fortify SAST 스캔을 repo 단위로 순회 실행하고 심각도 요약을 md로 출력한다.
# 관련 티켓: DEV2-7594 (월례 정기 점검), 프로세스 수립은 DEV2-7591.
#
# 설계 근거
#   - 스캔 단위는 서비스가 아니라 repo. max 하나에 스캐너 flavor 3종이 섞여 있다.
#   - 기준 브랜치는 origin/main, 없으면 origin/master (팀 결정 2026-07-29).
#   - 사용자 작업 트리를 건드리지 않기 위해 git worktree로 기준 브랜치를 별도 체크아웃한다.
#     스캔 대상 repo 7/10이 feature·deploy 브랜치에 있고 일부는 uncommitted 변경을 보유한다.
#   - Fortify translate에는 디렉토리(`.`)가 아니라 스택별 명시 글로브를 넘긴다.
#     `.`를 넘기면 Fortify 자체 파일 워커가 소스를 대량 누락한다 (AASM: TS 169파일 중 60만 번역).
#   - .NET(C#/VB.NET)은 macOS에서 SonarQube·Fortify 모두 불가.
#     SonarQube는 Roslyn 기반 MSBuild 스캐너가 필요하고, Fortify는 다음을 반환한다:
#     ".NET translation is only supported on Windows and Linux."
#     해당 repo는 SKIP으로 명시 기록하고 exit code로 구분한다.
#
# 보안 주의 (실측 기반, 축소해 말하지 않는다)
#   토큰 값은 Keychain에서만 읽는다. 그러나 스캐너 3종 모두 토큰을 프로세스 argv 또는
#   환경으로 받으므로 같은 UID의 `ps -ww` / `ps eww`에서 관찰될 수 있다.
#     - sonar-scanner CLI : SONAR_TOKEN 환경변수 사용 (argv 노출 회피)
#     - curl             : --config 로 stdin 전달 (argv 노출 회피)
#     - SonarScanner .NET: /d:sonar.token argv 필수. 환경변수 미지원 → argv 노출 잔존
#   즉 이 스크립트는 단일 사용자 머신 또는 전용 러너를 전제로 한다. 공용 호스트에서는
#   .NET 스캔 경로에 프로세스 격리가 필요하다.
#
# 사용법
#   run-static-scan.sh [옵션] <대상...>
#
#   대상:  all | repo 키 | svc:<서비스>
#          repo 키가 서비스명보다 우선한다. `tobe`는 repo 키(tobe/Tobe)로 해석되므로
#          tobe 서비스 전체를 돌리려면 `svc:tobe` 를 쓴다.
#
#   옵션:
#     --sonar-only        SonarQube만 실행
#     --fortify-only      Fortify만 실행
#     --dry-run           실행 계획만 출력 (스캔·네트워크 호출 없음)
#     --keep-worktree     스캔 후 임시 worktree를 남긴다 (디버깅용)
#     --fail-on-skip      커버리지 공백(SKIP)이 있으면 exit 1
#     --out-dir <path>    결과 출력 루트 (기본: ~/Documents/Work/static-scan)
#     -h, --help          도움말
#
#   종료 코드:
#     0  전 대상 완전 스캔
#     2  완료했으나 커버리지 공백(SKIP) 또는 부분 결과(PARTIAL) 존재
#     1  실패 발생 (또는 --fail-on-skip 지정 시 SKIP 존재)
#
# 사전 조건
#   - sonar-scanner (brew), dotnet SDK 8 + dotnet-sonarscanner(**arm64**), Fortify SAST 26.2.0
#     주의: `dotnet tool install --global dotnet-sonarscanner` 는 x86_64 apphost를 설치할 수 있다.
#     arm64 Mac에서는 `--arch arm64` 를 붙여야 libhostfxr 로드 실패를 피한다.
#   - Keychain 항목 sonarqube-jmkim-token (SonarQube user token, scan+provisioning 권한)

set -euo pipefail

# ── 설정 ────────────────────────────────────────────────────────────────────

readonly SONAR_HOST="https://sonarqube.sec.aladin.co.kr"
readonly SONAR_TOKEN_KEYCHAIN_SERVICE="sonarqube-jmkim-token"
readonly FORTIFY_HOME="${FORTIFY_HOME:-$HOME/Applications/Fortify/SAST_26.2.0}"
readonly WORKSPACE_ROOT="${WORKSPACE_ROOT:-$HOME/Documents/workspace}"
readonly DOTNET_SONAR_SCANNER="${DOTNET_SONAR_SCANNER:-$HOME/.dotnet/tools/dotnet-sonarscanner}"
readonly FORTIFY_HEAP="${FORTIFY_HEAP:-4G}"

# 테스트 코드 제외 패턴 (2026-07-30 확정).
#
# 실측 근거: NaruServer는 코드가 1월 이후 한 줄도 안 바뀌었는데 high 4 → 38로 늘었다.
# 원인은 1월 스캔이 src/test 를 제외했고 이번 스캔이 포함한 것이다(38건 중 24건이 src/test).
# 테스트 코드에 프로덕션 규칙을 적용하면 결함 수가 부풀고 커버리지 분모도 왜곡된다.
#
# 디렉토리명 기반 `**/test/**` 는 쓰지 않는다. 운영 코드를 버린다:
#   Tobe      Aladin.ToBe.Web/{Views,ViewsReact}/App/Test/**  Applink·Bridge·Device 앱 연동 뷰 12파일
#   max-front src/components/test/**                          AppLinkTest·BridgeTest 등 디버깅 페이지 7파일
# 둘 다 배포되는 운영 코드다. 경로 패턴은 규약이 확실한 곳만 쓴다.
#
# Kotlin은 파일명만으로 부족하다 — TestConfiguration.kt·TestFixtures.kt 3건이 Test* 접두어라
# `*Test.kt` 에 안 걸린다. src/test/ 경로로 잡는다 (Gradle 규약이라 운영 코드가 없다).
readonly TEST_EXCLUDES="**/src/test/**,**/src/testFixtures/**,e2e/**,.devops/tests/**,**/cypress/**,**/playwright/**,**/*.test.ts,**/*.test.tsx,**/*.test.js,**/*.test.jsx,**/*.test.mjs,**/*.spec.ts,**/*.spec.tsx,**/*.spec.js,**/*.spec.jsx,**/*Test.cs,**/*Tests.cs"

# Fortify translate 후 번역 파일 수가 git 추적 파일 수의 이 비율 미만이면 PARTIAL로 본다.
readonly COVERAGE_THRESHOLD_PCT=90

# SonarQube 분석은 서버 큐에서 비동기 처리된다. CE task 완료를 이만큼 기다린다.
readonly CE_POLL_MAX_SEC=300
readonly CE_POLL_INTERVAL_SEC=5

# ── repo 레지스트리 ─────────────────────────────────────────────────────────
#
# 문자열 구분자 파싱은 쓰지 않는다 (비고에 `|`가 들어가면 잘린다). case 조회로 전역에 채운다.
#
#   R_PATH         WORKSPACE_ROOT 기준 상대 경로
#   R_REF          기준 ref
#   R_SONARKEY     서버의 기존 projectKey (없으면 자동 생성됨)
#   R_SMODE        cli | dotnet | cli-nocs | skip-msbuild
#   R_FMODE        yes | nocs | skip-dotnet
#   R_GLOBS        Fortify translate 대상 글로브 (스택별, 공백 구분)
#   R_BUILD_TARGET dotnet 모드에서 빌드할 sln/csproj 상대 경로
#   R_SRCDIRS      Fortify translate 소스 루트 (공백 구분, 미지정 시 repo 전체)
#   R_HEAP         Fortify JVM 힙 (미지정 시 FORTIFY_HEAP)
#   R_NOTE         비고
#
# 소유권 근거: catalog/max.yaml, catalog/tobe.yaml 의 repos: 주석.
# 타팀 관리(ToBeAndroid·ToBeIos·max-search·Ebook*)와 git repo 아닌 사본은 제외했다.

# REGISTRY_ORDER 는 보고서 정렬 기준이며 레지스트리에 정의된 전체 키다.
# ALL_KEYS 는 `all` 이 실제로 도는 점검 대상이다.
# max-db-script·tobe-db-script 는 점검 대상에서 제외 (2026-07-30 결정). 정의는 남겨 둬
# 개별 키 지정으로는 여전히 실행 가능하고, 대상 복원 시 ALL_KEYS 에 다시 넣으면 된다.
readonly REGISTRY_ORDER="aasm naru-server max-server max-front maxcms-front maxcms-api max-db-script tobe-db-script max-api tobe"
readonly ALL_KEYS="aasm naru-server max-server max-front maxcms-front maxcms-api max-api tobe"

# 스택별 글로브. 소스 + 설정 파일(configuration 분석기 대상)을 함께 넘긴다.
readonly GLOBS_TS='**/*.ts **/*.tsx **/*.js **/*.jsx **/*.json **/*.yml **/*.yaml'
readonly GLOBS_KOTLIN='**/*.kt **/*.kts **/*.java **/*.yml **/*.yaml **/*.xml'
readonly GLOBS_TSQL='**/*.sql'
readonly GLOBS_WEB_NOCS='**/*.js **/*.jsx **/*.cshtml **/*.aspx **/*.ascx **/*.config'

load_repo() {
  R_PATH=""; R_REF=""; R_SONARKEY=""; R_SMODE=""; R_FMODE=""
  R_GLOBS=""; R_BUILD_TARGET=""; R_NOTE=""; R_HEAP=""; R_SRCDIRS=""
  case "$1" in
    aasm)
      R_PATH="AASM"; R_REF="origin/main"; R_SONARKEY="aasm"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_TS"
      # 6월 선례(DEV2-6294)가 app/components/lib 131파일로 스코프를 한정했다. repo 전체를 넘기면
      # package-lock.json·tests·docker 픽스처가 Critical로 잡혀 게이트를 막는다 (실측 11/15건).
      R_SRCDIRS="app components lib"
      R_NOTE="Next.js/TS. sonar-project.properties 보유(템플릿 원본). main이 deploy/prod보다 42커밋 뒤" ;;
    naru-server)
      R_PATH="naru/NaruServer"; R_REF="origin/main"; R_SONARKEY="NaruServer"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_KOTLIN"
      R_NOTE="Kotlin/Spring. main은 2026-01 이후 정지(개발은 develop) — 1월 baseline과 결과 유사 예상" ;;
    max-server)
      R_PATH="max/MaxServer"; R_REF="origin/main"; R_SONARKEY="MaxServer"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_KOTLIN"
      R_NOTE="Kotlin 전환용. fortify/scan-filter.txt 보유 — scan 단계 인자로 적용" ;;
    max-front)
      R_PATH="max/max-front"; R_REF="origin/main"; R_SONARKEY="max-front"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_TS"
      R_NOTE="Next.js 14.2.3/TS" ;;
    maxcms-front)
      R_PATH="max/maxcms-front"; R_REF="origin/main"; R_SONARKEY="maxcms-front"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_TS"
      R_NOTE="Next.js 14.2.35/TS" ;;
    maxcms-api)
      R_PATH="max/maxcms-api"; R_REF="origin/main"; R_SONARKEY="maxcms-api"
      R_SMODE="dotnet"; R_FMODE="skip-dotnet"; R_GLOBS=""
      R_BUILD_TARGET="Aladin.MaxCms/Aladin.MaxCms.sln"
      R_NOTE=".NET 8. Sonar 가능(MSBuild 스캐너), Fortify는 macOS .NET 미지원" ;;
    max-db-script)
      R_PATH="max/max-db-script"; R_REF="origin/master"; R_SONARKEY="max-db-script"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_TSQL"
      R_NOTE="T-SQL. SonarQube 프로젝트 신규 생성 대상" ;;
    tobe-db-script)
      R_PATH="tobe/tobe-db-script"; R_REF="origin/master"; R_SONARKEY="tobe-db-script"
      R_SMODE="cli"; R_FMODE="yes"; R_GLOBS="$GLOBS_TSQL"
      R_NOTE="T-SQL. SonarQube 프로젝트 신규 생성 대상" ;;
    max-api)
      R_PATH="max/max-api"; R_REF="origin/main"; R_SONARKEY="max-api"
      R_SMODE="skip-msbuild"; R_FMODE="skip-dotnet"; R_GLOBS=""
      R_NOTE=".NET FW 4.8. C# 400파일 SAST 경로 없음. 서버 이력의 xml=2651은 C# 0줄을 의미" ;;
    tobe)
      R_PATH="tobe/Tobe"; R_REF="origin/main"; R_SONARKEY="tobe"
      R_SMODE="cli-nocs"; R_FMODE="nocs"; R_GLOBS="$GLOBS_WEB_NOCS"
      # 212k ncloc·675 JS로 대상 중 최대. 4G로는 "not enough memory available to
      # complete analysis"로 scan이 실패한다 (2026-07-29 실측).
      R_HEAP="12G"
      R_NOTE=".NET FW 4.8 + JS/CSS. C# 596파일 공백, 프론트 자산만 커버" ;;
    *) return 1 ;;
  esac
  return 0
}

service_repos() {
  case "$1" in
    aasm) echo "aasm" ;;
    naru) echo "naru-server" ;;
    max)  echo "max-server max-front maxcms-front maxcms-api max-api" ;;
    tobe) echo "tobe" ;;
    *)    return 1 ;;
  esac
}

# ── 유틸 ────────────────────────────────────────────────────────────────────

SONAR_ONLY=false
FORTIFY_ONLY=false
DRY_RUN=false
KEEP_WORKTREE=false
FAIL_ON_SKIP=false
OUT_ROOT="$HOME/Documents/Work/static-scan"
TARGETS=""

log()  { printf '%s\n' "$*" >&2; }
info() { printf '  %s\n' "$*" >&2; }
warn() { printf 'WARN  %s\n' "$*" >&2; }
die()  { printf 'ERROR %s\n' "$*" >&2; exit 1; }

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'; exit 0; }

# ── 인자 파싱 ───────────────────────────────────────────────────────────────

while [ $# -gt 0 ]; do
  case "$1" in
    --sonar-only)    SONAR_ONLY=true; shift ;;
    --fortify-only)  FORTIFY_ONLY=true; shift ;;
    --dry-run)       DRY_RUN=true; shift ;;
    --keep-worktree) KEEP_WORKTREE=true; shift ;;
    --fail-on-skip)  FAIL_ON_SKIP=true; shift ;;
    --out-dir)       OUT_ROOT="${2:?--out-dir 값 누락}"; shift 2 ;;
    -h|--help)       usage ;;
    -*)              die "알 수 없는 옵션: $1" ;;
    *)               TARGETS="$TARGETS $1"; shift ;;
  esac
done

[ -n "$TARGETS" ] || die "대상을 지정해라. 예: $0 all  |  $0 --help"
if $SONAR_ONLY && $FORTIFY_ONLY; then
  die "--sonar-only 와 --fortify-only 는 동시에 쓸 수 없다"
fi

# 대상 전개 → 레지스트리 순서 유지 + 중복 제거
REQUESTED=""
for t in $TARGETS; do
  case "$t" in
    all)
      REQUESTED="$REQUESTED $ALL_KEYS" ;;
    svc:*)
      # 명시적 서비스 지정. `tobe`처럼 repo 키와 서비스명이 겹칠 때 쓴다.
      if svc=$(service_repos "${t#svc:}" 2>/dev/null); then
        REQUESTED="$REQUESTED $svc"
      else
        die "알 수 없는 서비스: ${t#svc:} (aasm naru max tobe)"
      fi ;;
    *)
      # repo 키를 서비스명보다 먼저 본다. 더 구체적인 쪽이 이겨야 한다.
      # (예전에는 서비스를 먼저 봐서 `tobe` 단건 지정이 불가능했다)
      if load_repo "$t" 2>/dev/null; then
        REQUESTED="$REQUESTED $t"
      elif svc=$(service_repos "$t" 2>/dev/null); then
        REQUESTED="$REQUESTED $svc"
      else
        die "알 수 없는 대상: $t (서비스: svc:aasm svc:naru svc:max svc:tobe / repo 키는 --help 참조)"
      fi ;;
  esac
done

SELECTED=""
for k in $REGISTRY_ORDER; do
  for r in $REQUESTED; do
    if [ "$r" = "$k" ]; then SELECTED="$SELECTED $k"; break; fi
  done
done
SELECTED="${SELECTED# }"
SELECTED_COUNT=$(printf '%s\n' $SELECTED | wc -l | tr -d ' ')

# ── 실행별 임시 루트 + 정리 trap ────────────────────────────────────────────
#
# 환경으로 주입된 경로를 지우지 않도록 실행마다 mktemp -d로 고유 루트를 만들고,
# 정리 대상은 그 prefix 아래로 한정한다. Ctrl-C에도 worktree가 남지 않게 trap을 건다.

RUN_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/team2-static-scan.XXXXXX") || die "임시 디렉토리 생성 실패"
RUN_ROOT=$(cd "$RUN_ROOT" && pwd -P)
ACTIVE_SRC=""
ACTIVE_WT=""
ACTIVE_BUILDID=""

remove_worktree() {
  local src="$1" wt="$2" real
  [ -n "$src" ] && [ -n "$wt" ] || return 0
  real=$(cd "$wt" 2>/dev/null && pwd -P || echo "")
  case "$real" in
    "$RUN_ROOT"/*) : ;;
    *) warn "정리 건너뜀 (RUN_ROOT 밖 경로): ${real:-$wt}"; return 0 ;;
  esac
  git -C "$src" worktree remove --force "$wt" >/dev/null 2>&1 || rm -rf "$real"
  git -C "$src" worktree prune >/dev/null 2>&1 || true
}

on_exit() {
  local rc=$?
  if [ -n "$ACTIVE_WT" ] && ! $KEEP_WORKTREE; then
    remove_worktree "$ACTIVE_SRC" "$ACTIVE_WT"
  fi
  if [ -n "$ACTIVE_BUILDID" ] && [ -x "$FORTIFY_HOME/bin/sourceanalyzer" ]; then
    "$FORTIFY_HOME/bin/sourceanalyzer" -b "$ACTIVE_BUILDID" -clean >/dev/null 2>&1 || true
  fi
  if ! $KEEP_WORKTREE; then
    case "$RUN_ROOT" in
      "${TMPDIR:-/tmp}"*|/tmp/*|/private/*) rmdir "$RUN_ROOT" 2>/dev/null || rm -rf "$RUN_ROOT" ;;
    esac
  else
    log "임시 루트 유지: $RUN_ROOT"
  fi
  exit $rc
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

# ── 사전 점검 ───────────────────────────────────────────────────────────────

SONAR_TOKEN=""
NEED_DOTNET=false

preflight() {
  local need_sonar=true need_fortify=true k
  $FORTIFY_ONLY && need_sonar=false
  $SONAR_ONLY && need_fortify=false

  command -v git >/dev/null || die "git 없음"

  for k in $SELECTED; do
    load_repo "$k"
    [ "$R_SMODE" = "dotnet" ] && NEED_DOTNET=true
  done

  if $need_sonar; then
    command -v sonar-scanner >/dev/null || die "sonar-scanner 없음 (brew install sonar-scanner)"
    SONAR_TOKEN=$(security find-generic-password -s "$SONAR_TOKEN_KEYCHAIN_SERVICE" -w 2>/dev/null || true)
    [ -n "$SONAR_TOKEN" ] || die "Keychain 항목 '$SONAR_TOKEN_KEYCHAIN_SERVICE' 없음 또는 빈 값"

    if ! $DRY_RUN; then
      local valid
      valid=$(sonar_api "/api/authentication/validate" || echo '{}')
      case "$valid" in
        *'"valid":true'*) : ;;
        *) die "SonarQube 토큰 무효 또는 서버 연결 실패 ($SONAR_HOST)" ;;
      esac
    fi

    if $NEED_DOTNET; then
      command -v dotnet >/dev/null || die "dotnet SDK 없음"
      resolve_dotnet_root
      # 목록 조회로는 부족하다. 설치본 아키텍처가 런타임과 다르면 실행 시점에 죽는다.
      [ -x "$DOTNET_SONAR_SCANNER" ] || \
        die "dotnet-sonarscanner 없음: $DOTNET_SONAR_SCANNER
     설치: dotnet tool install --global dotnet-sonarscanner --arch arm64"
      local ver
      ver=$("$DOTNET_SONAR_SCANNER" --version 2>&1 || true)
      case "$ver" in
        *"SonarScanner for .NET"*) : ;;
        *"You must install .NET"*)
          die "dotnet-sonarscanner가 런타임을 못 찾는다 (DOTNET_ROOT=${DOTNET_ROOT:-unset})
     homebrew dotnet@8은 apphost 기본 탐색 경로에 런타임을 두지 않는다. 예:
       export DOTNET_ROOT=/opt/homebrew/opt/dotnet@8/libexec" ;;
        *"incompatible architecture"*)
          die "dotnet-sonarscanner 아키텍처 불일치 ($DOTNET_SONAR_SCANNER)
     arm64 Mac에 x86_64 apphost가 설치됐다. 재설치:
       dotnet tool uninstall --global dotnet-sonarscanner
       dotnet tool install --global dotnet-sonarscanner --arch arm64" ;;
        *)
          die "dotnet-sonarscanner 실행 불가 ($DOTNET_SONAR_SCANNER)
     출력: $(printf '%s' "$ver" | head -2 | tr '\n' ' ')" ;;
      esac
    fi
  fi

  if $need_fortify; then
    [ -x "$FORTIFY_HOME/bin/sourceanalyzer" ] || die "sourceanalyzer 없음: $FORTIFY_HOME/bin"
    [ -x "$FORTIFY_HOME/bin/FPRUtility" ] || die "FPRUtility 없음: $FORTIFY_HOME/bin"
    [ -f "$FORTIFY_HOME/fortify.license" ] || warn "Fortify 라이선스 파일이 $FORTIFY_HOME 에 없다"
  fi
}

# dotnet-sonarscanner의 apphost는 DOTNET_ROOT로 런타임을 찾는다. homebrew dotnet@8은
# apphost 기본 탐색 경로(/usr/local/share/dotnet 등)에 런타임을 두지 않으므로 직접 잡아준다.
resolve_dotnet_root() {
  [ -n "${DOTNET_ROOT:-}" ] && [ -d "${DOTNET_ROOT:-}" ] && return 0
  local sdk_dir
  sdk_dir=$(dotnet --list-sdks 2>/dev/null | sed -n '1s/.*\[\(.*\)\]$/\1/p')
  case "$sdk_dir" in
    */sdk) DOTNET_ROOT="${sdk_dir%/sdk}"; export DOTNET_ROOT ;;
  esac
}

# 토큰을 argv에 두지 않기 위해 curl --config 를 stdin으로 먹인다.
sonar_api() {
  local path="$1"
  printf 'header = "Authorization: Bearer %s"\n' "$SONAR_TOKEN" \
    | curl -fsS -m 30 --config - "$SONAR_HOST$path" 2>/dev/null
}

# ── worktree 준비 ───────────────────────────────────────────────────────────

prepare_worktree() {
  local key="$1" relpath="$2" ref="$3"
  local src="$WORKSPACE_ROOT/$relpath"
  local wt="$RUN_ROOT/$key"

  [ -d "$src/.git" ] || { warn "$key: git repo 아님 ($src)"; return 1; }
  git -C "$src" fetch --quiet origin 2>/dev/null || warn "$key: fetch 실패, 로컬 ref로 진행"

  local resolved="$ref" alt=""
  if ! git -C "$src" rev-parse --verify --quiet "$ref" >/dev/null 2>&1; then
    case "$ref" in
      origin/main)   alt=origin/master ;;
      origin/master) alt=origin/main ;;
    esac
    if [ -n "$alt" ] && git -C "$src" rev-parse --verify --quiet "$alt" >/dev/null 2>&1; then
      warn "$key: $ref 없음 → $alt 사용"; resolved="$alt"
    else
      warn "$key: 기준 ref 없음 ($ref)"; return 1
    fi
  fi

  git -C "$src" worktree prune >/dev/null 2>&1 || true
  if ! git -C "$src" worktree add --detach --quiet "$wt" "$resolved" 2>/dev/null; then
    warn "$key: worktree 생성 실패"
    remove_worktree "$src" "$wt"
    return 1
  fi

  WT_PATH="$wt"; WT_SRC="$src"; WT_REF="$resolved"
  WT_SHA=$(git -C "$wt" rev-parse --short HEAD)
  WT_DATE=$(git -C "$wt" log -1 --format=%ad --date=short)
  ACTIVE_SRC="$src"; ACTIVE_WT="$wt"
  return 0
}

# ── SonarQube ───────────────────────────────────────────────────────────────

# scanner가 남기는 report-task.txt의 ceTaskId로 서버 큐 처리 완료를 기다린다.
# 이 확인 없이 measures를 읽으면 기존 프로젝트는 '이전 분석값'을 즉시 돌려준다.
wait_ce_task() {
  local src="$1" logfile="$2" taskfile ce_id waited status resp unknown=0
  # CLI 스캐너는 .scannerwork/, SonarScanner for .NET은 .sonarqube/out/.sonar/ 에 남긴다.
  # 경로를 scannerwork로 한정하면 .NET 스캔이 항상 NO_TASK_FILE로 떨어진다 (2026-07-29 실측).
  taskfile=$(find "$src" -name report-task.txt -type f 2>/dev/null \
             | grep -E '(scannerwork|sonarqube)' | head -1)
  [ -n "$taskfile" ] || taskfile=$(find "$src" -name report-task.txt -type f 2>/dev/null | head -1)
  [ -n "$taskfile" ] || { CE_STATE="NO_TASK_FILE"; return 1; }
  # CRLF·공백이 섞이면 URL이 깨져 API가 400을 돌려준다.
  ce_id=$(sed -n 's/^ceTaskId=//p' "$taskfile" | head -1 | tr -d ' \t\r\n')
  [ -n "$ce_id" ] || { CE_STATE="NO_TASK_ID"; return 1; }
  printf 'ceTaskId=%s\n' "$ce_id" >> "$logfile"

  waited=0
  while [ "$waited" -lt "$CE_POLL_MAX_SEC" ]; do
    resp=$(sonar_api "/api/ce/task?id=$ce_id" || true)
    status=$(printf '%s' "$resp" | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([A-Z_]*\)".*/\1/p' | head -1)
    case "$status" in
      SUCCESS)             CE_STATE="SUCCESS"; return 0 ;;
      FAILED|CANCELED)     CE_STATE="$status"; return 1 ;;
      PENDING|IN_PROGRESS) unknown=0 ;;
      *)
        # 빈 응답·일시적 오류는 재시도한다. 연속으로 반복되면 그때 실패로 본다.
        unknown=$((unknown + 1))
        printf 'ce poll unexpected (%s): %s\n' "$unknown" "$(printf '%s' "$resp" | head -c 200)" >> "$logfile"
        if [ "$unknown" -ge 5 ]; then
          CE_STATE="UNKNOWN:${status:-empty}"; return 1
        fi
        ;;
    esac
    sleep "$CE_POLL_INTERVAL_SEC"
    waited=$((waited + CE_POLL_INTERVAL_SEC))
  done
  CE_STATE="TIMEOUT_${CE_POLL_MAX_SEC}s"
  return 1
}

run_sonar() {
  local key="$1" mode="$2" projkey="$3" src="$4" logfile="$5" build_target="$6" version="${7:-}"

  if [ "$mode" = "skip-msbuild" ]; then
    SONAR_RESULT="SKIP"
    SONAR_NOTE=".NET Framework — Roslyn/MSBuild 스캐너 필요, macOS 불가"
    return 0
  fi

  if $DRY_RUN; then
    SONAR_RESULT="DRY"; SONAR_NOTE="$mode → $projkey"
    return 0
  fi

  local -a args=(
    "-Dsonar.projectKey=$projkey"
    "-Dsonar.scm.provider=git"
  )
  # New Code 기준이 PREVIOUS_VERSION인데 projectVersion이 분석 간 동일하면 leak period가
  # 리셋되지 않고 첫 분석 이후로 계속 누적된다 (실측: 6개월 공백 → new_violations 37~233).
  # 커밋 날짜+SHA를 버전으로 넣어 분석마다 버전이 바뀌게 하고, new code를 "지난 분석 이후"로 맞춘다.
  [ -n "$version" ] && args+=("-Dsonar.projectVersion=$version")
  if [ ! -f "$src/sonar-project.properties" ]; then
    args+=("-Dsonar.sources=.")
    args+=("-Dsonar.exclusions=$(sonar_exclusions "$mode")")
  fi
  case "$key" in
    *-db-script)
      # T-SQL 분석기 기본 확장자는 .tsql 이라 .sql을 명시하지 않으면 아무것도 잡히지 않는다.
      # .sql 소유권이 PL/SQL 분석기와 충돌하므로 PL/SQL 쪽은 비충돌 확장자로 밀어둔다.
      args+=("-Dsonar.tsql.file.suffixes=.sql,.tsql")
      args+=("-Dsonar.plsql.file.suffixes=.pks,.pkb")
      ;;
  esac

  local rc=0
  case "$mode" in
    cli|cli-nocs)
      # SONAR_TOKEN/SONAR_HOST_URL 환경으로 넘겨 argv 노출을 없앤다.
      ( cd "$src" && SONAR_TOKEN="$SONAR_TOKEN" SONAR_HOST_URL="$SONAR_HOST" \
          sonar-scanner "${args[@]}" ) >>"$logfile" 2>&1 || rc=$?
      ;;
    dotnet)
      local target="$build_target"
      [ -n "$target" ] || target="."
      if [ "$target" != "." ] && [ ! -f "$src/$target" ]; then
        SONAR_RESULT="FAIL"; SONAR_NOTE="빌드 대상 없음: $target"
        return 0
      fi
      # SonarScanner for .NET은 SONAR_TOKEN 환경을 읽지 않는다. argv 노출은 문서화된 잔존 위험.
      ( cd "$src" \
        && "$DOTNET_SONAR_SCANNER" begin \
             "/k:$projkey" ${version:+"/v:$version"} \
             "/d:sonar.host.url=$SONAR_HOST" "/d:sonar.token=$SONAR_TOKEN" \
        && dotnet build "$target" --nologo -v minimal \
        && "$DOTNET_SONAR_SCANNER" end "/d:sonar.token=$SONAR_TOKEN" \
      ) >>"$logfile" 2>&1 || rc=$?
      ;;
  esac

  if [ $rc -ne 0 ]; then
    SONAR_RESULT="FAIL"; SONAR_NOTE="scanner rc=$rc — 로그: $logfile"
    return 0
  fi

  CE_STATE=""
  if wait_ce_task "$src" "$logfile"; then
    SONAR_RESULT="OK"; SONAR_NOTE="$projkey (CE SUCCESS)"
  else
    SONAR_RESULT="PARTIAL"
    SONAR_NOTE="$projkey — 업로드는 됐으나 서버 처리 확인 실패 (CE=$CE_STATE). 측정값은 이전 분석일 수 있다"
  fi
}

sonar_exclusions() {
  local base='**/node_modules/**,**/.next/**,**/dist/**,**/build/**,**/bin/**,**/obj/**,**/coverage/**,**/vendor/**,**/*.min.js,**/*.min.css'
  base="$base,$TEST_EXCLUDES"
  case "$1" in
    cli-nocs) printf '%s,%s' "$base" '**/*.cs,**/*.vb' ;;
    *)        printf '%s' "$base" ;;
  esac
}

fetch_sonar_measures() {
  local projkey="$1"
  local metrics="ncloc,software_quality_blocker_issues,software_quality_high_issues,ncloc_language_distribution"
  sonar_api "/api/measures/component?component=$projkey&metricKeys=$metrics" || true
}

# ── Fortify ─────────────────────────────────────────────────────────────────

# git 추적 파일 중 글로브에 해당하는 수. translate 커버리지 대조 기준.
# translate가 실제로 넘기는 대상과 같은 제외 규칙을 적용해야 한다.
# 분모가 다르면 커버리지 게이트가 거짓 PARTIAL을 낸다
# (실측: tobe에서 min.js 104건이 분모에만 남아 84%로 오판됐다).
readonly EXPECTED_EXCLUDE_RE='(^|/)(node_modules|\.next|dist|build|bin|obj|coverage|vendor)/|\.min\.(js|css)$|(^|/)docs/|\.md$|/src/test/|/src/testFixtures/|(^|/)(e2e|cypress|playwright)/|(^|/)\.devops/tests/|\.(test|spec)\.[jt]sx?$|\.test\.mjs$|(Test|Tests)\.cs$'

expected_file_count() {
  local src="$1" globs="$2" mode="$3" srcdirs="${4:-}" total=0 g ext n re d pathspec
  re="$EXPECTED_EXCLUDE_RE"
  # nocs 모드는 C#·VB를 넘기지 않는다. ASP.NET 뷰(.aspx/.ascx/.cshtml)는 인라인 C#을 담고 있어
  # macOS Fortify가 번역을 거부하므로 분모에서도 빼야 한다.
  [ "$mode" = "nocs" ] && re="$re|\.(cs|vb|aspx|ascx)$"
  # 셸 확장을 막는다. 확장되면 g가 실제 경로가 되어 확장자 추출이 깨진다.
  set -f
  for g in $globs; do
    ext="${g##*.}"
    if [ -n "$srcdirs" ]; then
      n=0
      for d in $srcdirs; do
        pathspec=$(git -C "$src" ls-files "$d/*.$ext" 2>/dev/null | grep -vE "$re" | wc -l | tr -d ' ')
        n=$((n + pathspec))
      done
    else
      n=$(git -C "$src" ls-files "*.$ext" 2>/dev/null | grep -vE "$re" | wc -l | tr -d ' ')
    fi
    total=$((total + n))
  done
  set +f
  printf '%s' "$total"
}

# Fortify는 내부 분석 오류가 있어도 FPR을 만들고 rc=0을 돌려준다. 로그와 FPR 오류를 직접 본다.
fortify_health() {
  local fpr="$1" logfile="$2" errs=0 logbad=0
  errs=$("$FORTIFY_HOME/bin/FPRUtility" -information -errors -project "$fpr" 2>/dev/null \
         | grep -cE 'Fatal|code [0-9]+|Unexpected exception' || true)
  logbad=$(grep -cE 'results may be incomplete|Unexpected exception|Fatal:' "$logfile" 2>/dev/null || true)
  printf '%s %s' "${errs:-0}" "${logbad:-0}"
}

# -analyzerIssueCounts는 analyzer 그룹 수이고 심각도가 아니다.
# 게이트 기준(Critical/High)에 맞춰 priority별로 센다.
# 파싱 실패를 0으로 떨어뜨리면 "Critical 0건"이라는 거짓 통과가 나온다. 실패는 실패로 알린다.
# 출력은 "N issues of M matched search query." 또는 "No issues matched search query."
SEV_PARSE_OK=true
fortify_severity() {
  local fpr="$1" v raw n out=""
  SEV_PARSE_OK=true
  for v in critical high medium low; do
    raw=$("$FORTIFY_HOME/bin/FPRUtility" -information -search -project "$fpr" \
            -query "[fortify priority order]:$v" 2>/dev/null | head -1)
    case "$raw" in
      "No issues matched"*) n=0 ;;
      [0-9]*" issues of "*)  n="${raw%% *}" ;;
      *) n="?"; SEV_PARSE_OK=false ;;
    esac
    out="$out $v=$n"
  done
  printf '%s' "${out# }"
}

run_fortify() {
  local key="$1" mode="$2" src="$3" globs="$4" outdir="$5" logfile="$6" heap="${7:-}" srcdirs="${8:-}"
  [ -n "$heap" ] || heap="$FORTIFY_HEAP"
  local sa="$FORTIFY_HOME/bin/sourceanalyzer"
  local buildid="team2-$RUN_STAMP-$key-$$"
  local fpr="$outdir/$key.fpr"

  if [ "$mode" = "skip-dotnet" ]; then
    FORTIFY_RESULT="SKIP"
    FORTIFY_NOTE=".NET translation은 Windows/Linux만 지원 (macOS가 거부)"
    return 0
  fi
  if $DRY_RUN; then
    FORTIFY_RESULT="DRY"; FORTIFY_NOTE="translate+scan ($mode) → $key.fpr"
    return 0
  fi

  # translate 제외: 빌드 산출물·의존성 + 문서.
  # 문서를 빼는 이유는 실측 근거다. AASM 13 Critical 전부가 docs/*.md 의 환경변수 예시와
  # localstack 픽스처였다. 문서 예시로 "Critical 0건" 게이트가 막히면 게이트가 무의미해진다.
  local -a tr_excl=(
    -exclude "**/node_modules/**" -exclude "**/.next/**" -exclude "**/dist/**"
    -exclude "**/build/**" -exclude "**/bin/**" -exclude "**/obj/**"
    -exclude "**/vendor/**" -exclude "**/coverage/**"
    -exclude "**/*.min.js" -exclude "**/*.min.css"
    -exclude "**/docs/**" -exclude "**/*.md"
  )
  # 테스트 코드 제외 (TEST_EXCLUDES 와 동일 목록)
  local _te _ifs="$IFS"
  IFS=','
  for _te in $TEST_EXCLUDES; do tr_excl+=(-exclude "$_te"); done
  IFS="$_ifs"
  [ "$mode" = "nocs" ] && tr_excl+=(-exclude "**/*.cs" -exclude "**/*.vb")

  # -filter 는 scan 단계 인자다. translate에 주면 적용되지 않는다.
  local -a scan_args=()
  if [ "$key" = "max-server" ] && [ -f "$src/fortify/scan-filter.txt" ]; then
    scan_args+=(-filter "$src/fortify/scan-filter.txt")
  fi

  ACTIVE_BUILDID="$buildid"
  if ! "$sa" -b "$buildid" -clean >>"$logfile" 2>&1; then
    FORTIFY_RESULT="FAIL"; FORTIFY_NOTE="build state clean 실패 — 이전 상태 혼입 위험"
    return 0
  fi

  # 글로브는 Fortify가 직접 해석해야 한다. 셸이 먼저 확장하면 bash 3.2에는 globstar가 없어
  # `**/*.ts`가 한 단계만 매칭되고 재귀 탐색이 사라진다 (실측: AASM 193 → 70파일).
  # noglob으로 단어 분리만 하고 확장은 막은 뒤 리터럴 패턴을 그대로 넘긴다.
  local -a gl=()
  local g d
  set -f
  if [ -n "$srcdirs" ]; then
    # 소스 루트가 지정되면 글로브를 루트별로 전개한다 (`app/**/*.ts` 형태).
    for d in $srcdirs; do
      [ -d "$src/$d" ] || { set +f; warn "$key: 소스 루트 없음 ($d)"; set -f; continue; }
      for g in $globs; do gl+=("$d/$g"); done
    done
  else
    for g in $globs; do gl+=("$g"); done
  fi
  set +f
  if [ ${#gl[@]} -eq 0 ]; then
    FORTIFY_RESULT="FAIL"; FORTIFY_NOTE="translate 글로브 미정의 (레지스트리 R_GLOBS 확인)"
    return 0
  fi

  local rc=0
  ( cd "$src" && "$sa" -b "$buildid" -Xmx"$heap" "${tr_excl[@]}" "${gl[@]}" ) \
    >>"$logfile" 2>&1 || rc=$?
  if [ $rc -ne 0 ]; then
    FORTIFY_RESULT="FAIL"; FORTIFY_NOTE="translate rc=$rc — 로그: $logfile"
    return 0
  fi

  local translated expected pct ext_re
  # 분자·분모의 단위를 맞춘다. -show-files는 import 추적으로 글로브에 없는 확장자까지 세므로
  # (실측: lib/*.ts 30개 전달 시 결과에 .cjs 1건 포함) 그대로 비교하면 다른 확장자가
  # 누락분을 메워 임계를 통과하는 거짓 OK가 난다. Windows판(ps1)과 동일한 처리다.
  ext_re=$(printf '%s' "$globs" | tr ' ' '\n' | sed -n 's/.*\.\([A-Za-z0-9]*\)$/\1/p' \
           | sort -u | paste -sd'|' -)
  if [ -n "$ext_re" ]; then
    translated=$("$sa" -b "$buildid" -show-files 2>/dev/null \
                 | grep -icE "\.($ext_re)\$" || true)
  else
    translated=$("$sa" -b "$buildid" -show-files 2>/dev/null | wc -l | tr -d ' ')
  fi
  [ -n "$translated" ] || translated=0
  expected=$(expected_file_count "$src" "$globs" "$mode" "$srcdirs")
  if [ "${expected:-0}" -gt 0 ]; then
    pct=$(( translated * 100 / expected ))
  else
    pct=100
  fi

  rc=0
  "$sa" -b "$buildid" -Xmx"$heap" -scan "${scan_args[@]+"${scan_args[@]}"}" -f "$fpr" \
    >>"$logfile" 2>&1 || rc=$?
  if [ $rc -ne 0 ] || [ ! -f "$fpr" ]; then
    FORTIFY_RESULT="FAIL"
    if grep -q "not enough memory available" "$logfile" 2>/dev/null; then
      FORTIFY_NOTE="scan 메모리 부족 (-Xmx$heap) — 힙을 올리거나 머신이 한가할 때 재실행. 로그: $logfile"
    else
      FORTIFY_NOTE="scan rc=$rc — 로그: $logfile"
    fi
    return 0
  fi

  local health errs logbad sev
  health=$(fortify_health "$fpr" "$logfile")
  errs=${health%% *}; logbad=${health##* }
  sev=$(fortify_severity "$fpr")

  FORTIFY_NOTE="$sev | 번역 $translated/$expected (${pct}%) | fpr: $fpr"
  if ! $SEV_PARSE_OK; then
    FORTIFY_RESULT="PARTIAL"
    FORTIFY_NOTE="$FORTIFY_NOTE | 심각도 집계 파싱 실패 — 수치 신뢰 불가"
  elif [ "${errs:-0}" -gt 0 ] || [ "${logbad:-0}" -gt 0 ]; then
    FORTIFY_RESULT="PARTIAL"
    FORTIFY_NOTE="$FORTIFY_NOTE | 분석 오류 ${errs}건·로그 경고 ${logbad}건 — 결과 불완전"
  elif [ "$pct" -lt "$COVERAGE_THRESHOLD_PCT" ]; then
    FORTIFY_RESULT="PARTIAL"
    FORTIFY_NOTE="$FORTIFY_NOTE | 번역 커버리지 ${pct}% < ${COVERAGE_THRESHOLD_PCT}%"
  else
    FORTIFY_RESULT="OK"
  fi

  "$sa" -b "$buildid" -clean >/dev/null 2>&1 || true
  ACTIVE_BUILDID=""
}

# ── 실행 ────────────────────────────────────────────────────────────────────

RUN_DATE=$(date +%Y-%m-%d)
RUN_STAMP=$(date +%Y%m%d-%H%M%S)

preflight

OUT_DIR="$OUT_ROOT/$RUN_DATE"
LOG_DIR="$OUT_DIR/logs"
SUMMARY="$OUT_DIR/summary-$RUN_STAMP.md"
mkdir -p "$LOG_DIR"

log ""
log "정적 점검 실행 — 대상 $SELECTED_COUNT repo"
log "  기준 브랜치: origin/main (없으면 origin/master)"
log "  출력: $OUT_DIR"
$DRY_RUN && log "  ** DRY RUN — 실제 스캔 없음 **"
log ""

ROWS=""
DETAILS=""
SKIPS=""
PARTIALS=""
FAILS=""
add() { eval "$1=\"\${$1}\${$1:+\$NL}\$2\""; }
NL='
'

for key in $SELECTED; do
  load_repo "$key"
  log "[$key] $R_PATH ($R_REF)"

  if ! prepare_worktree "$key" "$R_PATH" "$R_REF"; then
    add ROWS "| \`$key\` | $R_REF | - | WORKTREE 실패 | WORKTREE 실패 |"
    add FAILS "- \`$key\`: worktree 준비 실패"
    ACTIVE_WT=""; ACTIVE_SRC=""
    continue
  fi
  info "worktree: $WT_REF @ $WT_SHA ($WT_DATE)"

  logfile="$LOG_DIR/$key.log"
  : > "$logfile"
  SONAR_RESULT="-"; SONAR_NOTE=""
  FORTIFY_RESULT="-"; FORTIFY_NOTE=""

  if ! $FORTIFY_ONLY; then
    run_sonar "$key" "$R_SMODE" "$R_SONARKEY" "$WT_PATH" "$logfile" "$R_BUILD_TARGET" "$WT_DATE-$WT_SHA"
    info "SonarQube: $SONAR_RESULT ${SONAR_NOTE:+— $SONAR_NOTE}"
  fi
  if ! $SONAR_ONLY; then
    run_fortify "$key" "$R_FMODE" "$WT_PATH" "$R_GLOBS" "$OUT_DIR" "$logfile" "$R_HEAP" "$R_SRCDIRS"
    info "Fortify:   $FORTIFY_RESULT ${FORTIFY_NOTE:+— $FORTIFY_NOTE}"
  fi

  measures=""
  if [ "$SONAR_RESULT" = "OK" ]; then
    measures=$(fetch_sonar_measures "$R_SONARKEY")
  fi

  add ROWS "| \`$key\` | ${WT_REF#origin/} | \`$WT_SHA\` ($WT_DATE) | $SONAR_RESULT | $FORTIFY_RESULT |"
  add DETAILS "### \`$key\`"
  add DETAILS ""
  add DETAILS "- 경로: \`$R_PATH\` @ \`$WT_REF\` (\`$WT_SHA\`, $WT_DATE)"
  add DETAILS "- 비고: $R_NOTE"
  add DETAILS "- SonarQube: **$SONAR_RESULT** ${SONAR_NOTE:+— $SONAR_NOTE}"
  add DETAILS "- Fortify: **$FORTIFY_RESULT** ${FORTIFY_NOTE:+— $FORTIFY_NOTE}"
  if [ -n "$measures" ]; then
    add DETAILS "- 측정값: \`$(printf '%s' "$measures" | tr -d '\n' | cut -c1-400)\`"
  fi
  add DETAILS ""

  for pair in "SonarQube:$SONAR_RESULT:$SONAR_NOTE" "Fortify:$FORTIFY_RESULT:$FORTIFY_NOTE"; do
    tool="${pair%%:*}"; rest="${pair#*:}"; res="${rest%%:*}"; nt="${rest#*:}"
    case "$res" in
      SKIP)    add SKIPS "- \`$key\` $tool: $nt" ;;
      PARTIAL) add PARTIALS "- \`$key\` $tool: $nt" ;;
      FAIL)    add FAILS "- \`$key\` $tool: $nt" ;;
    esac
  done

  remove_worktree "$WT_SRC" "$WT_PATH"
  ACTIVE_WT=""; ACTIVE_SRC=""
done

{
  printf '%s\n' "# 정적 점검 결과 — $RUN_DATE"
  printf '\n'
  printf '%s\n' "- 실행: \`$RUN_STAMP\`"
  printf '%s\n' "- 티켓: DEV2-7594"
  printf '%s\n' "- 기준 브랜치: \`origin/main\` 우선, 없으면 \`origin/master\`"
  printf '%s\n' "- SonarQube: $SONAR_HOST"
  printf '%s\n' "- 대상 repo: ${SELECTED_COUNT}개"
  $DRY_RUN && printf '%s\n' "- **DRY RUN — 실제 스캔 미수행**"
  printf '\n## 요약\n\n'
  printf '%s\n' "| repo | 기준 | commit | SonarQube | Fortify |"
  printf '%s\n' "|---|---|---|---|---|"
  printf '%s\n' "$ROWS"

  if [ -n "$FAILS" ]; then
    printf '\n## 실패\n\n'; printf '%s\n' "$FAILS"
  fi
  if [ -n "$PARTIALS" ]; then
    printf '\n## 부분 결과 (PARTIAL — 수치를 신뢰하지 말 것)\n\n'
    printf '%s\n' "$PARTIALS"
    printf '\n'
    printf '%s\n' "Fortify는 내부 분석 오류가 있어도 FPR을 만들고 rc=0을 반환한다."
    printf '%s\n' "PARTIAL은 FPR 오류·로그 경고 또는 번역 커버리지 미달을 뜻하므로 완전 스캔으로 취급하면 안 된다."
  fi
  if [ -n "$SKIPS" ]; then
    printf '\n## 커버리지 공백 (SKIP)\n\n'
    printf '%s\n' "$SKIPS"
    printf '\n'
    printf '%s\n' "SKIP은 도구 설정 문제가 아니라 플랫폼 제약이다. 해소에는 Windows 러너"
    printf '%s\n' "(SonarQube C#) 또는 Windows/Linux 호스트(Fortify .NET)가 필요하다. DEV2-7591 참조."
  fi
  printf '\n## 상세\n\n'
  printf '%s\n' "$DETAILS"
} > "$SUMMARY"

log ""
log "완료. 요약: $SUMMARY"

if [ -n "$FAILS" ]; then
  log "실패 있음 → exit 1"; exit 1
fi
if $FAIL_ON_SKIP && [ -n "$SKIPS" ]; then
  log "커버리지 공백 있음 (--fail-on-skip) → exit 1"; exit 1
fi
if [ -n "$SKIPS" ] || [ -n "$PARTIALS" ]; then
  log "공백/부분 결과 있음 → exit 2"; exit 2
fi
exit 0
