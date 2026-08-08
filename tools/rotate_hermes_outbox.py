#!/usr/bin/env python3
"""Hermes Discord outbox 회전 — 오래된 dispatch 산출물을 vault 밖으로 보관.

문제: `wiki/projects/agentic-os/hermes-discord-outbox/` 가 정리 없이 영구 누적
(2026-08-08 실측: 15,447 JSON / 74MB = vault git 추적 파일의 94.6%, iCloud 동기화 부담).

정책: 요청 디렉토리(hdr-*)의 **가장 최근 파일이 N일(기본 14) 경과**하면 아카이브로 이동.
이동이지 삭제가 아니다 — 되돌리기는 mv. 아카이브: `~/.hermes-team2/archive/discord-outbox/YYYY-MM/`

사용법:
    python3 tools/rotate_hermes_outbox.py            # dry-run (기본)
    python3 tools/rotate_hermes_outbox.py --apply
    python3 tools/rotate_hermes_outbox.py --days 30
"""
import argparse
import os
import shutil
import time

VAULT = os.environ.get("LOCAL_WIKI_PATH",
                       os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"))
OUTBOX = os.path.join(VAULT, "wiki/projects/agentic-os/hermes-discord-outbox")
ARCHIVE = os.path.expanduser("~/.hermes-team2/archive/discord-outbox")


def dir_latest_mtime(path):
    latest = os.path.getmtime(path)
    for base, _, files in os.walk(path):
        for f in files:
            try:
                latest = max(latest, os.path.getmtime(os.path.join(base, f)))
            except OSError:
                pass
    return latest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 이동 (기본은 dry-run)")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()

    if not os.path.isdir(OUTBOX):
        print(f"outbox 없음: {OUTBOX}")
        return
    cutoff = time.time() - a.days * 86400
    stale, active = [], 0
    for d in sorted(os.listdir(OUTBOX)):
        full = os.path.join(OUTBOX, d)
        if not os.path.isdir(full):
            continue
        if dir_latest_mtime(full) < cutoff:
            stale.append((d, full))
        else:
            active += 1

    files = sum(len(fs) for _, full in stale for _, _, fs in os.walk(full))
    print(f"대상: {len(stale)}개 요청 디렉토리 / {files:,}개 파일 ({a.days}일 경과) — 활성 유지 {active}개")
    if not a.apply:
        for d, _ in stale[:5]:
            print(f"  [dry-run] {d}")
        if len(stale) > 5:
            print(f"  … 외 {len(stale)-5}개. 실행: --apply")
        return

    month_dir = os.path.join(ARCHIVE, time.strftime("%Y-%m"))
    os.makedirs(month_dir, exist_ok=True)
    for d, full in stale:
        shutil.move(full, os.path.join(month_dir, d))
    print(f"이동 완료 → {month_dir}  (되돌리기: mv)")


if __name__ == "__main__":
    main()
