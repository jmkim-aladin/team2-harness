"""Human terminal confirmation shared by the production DB client paths."""
import os
import select
import sys
import termios
import tty


def _escape_key(fd):
    """Bound incomplete Escape sequences so Escape also cancels promptly."""
    sequence = b''
    for _ in range(2):
        if not select.select([fd], [], [], 0.15)[0]:
            return None
        sequence += os.read(fd, 1)
    return {b'[A': -1, b'OA': -1, b'[B': 1, b'OB': 1}.get(sequence)


def confirm_operator(title):
    """Return true only for a human's submitted approval; never read a pipe."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError('operator_terminal_required')
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    selected = 0
    labels = ('1 승인', '2 수정 요청', '3 취소')
    try:
        # Discard keys typed while the SQL review was still being printed.
        termios.tcflush(fd, termios.TCIFLUSH)
        tty.setcbreak(fd)
        print('\n' + title, flush=True)
        print('1 승인 / 2 수정 요청 / 3 취소 — 기본: 승인, Enter 확정, ↑↓ 선택', flush=True)
        while True:
            current = labels[selected] if selected is not None else '1·2·3 또는 방향키로 선택하세요'
            print('\r\033[2K> ' + current, end='', flush=True)
            key = os.read(fd, 1)
            if key in (b'\r', b'\n'):
                if selected is not None:
                    break
            elif key in (b'1', b'2', b'3'):
                selected = int(key) - 1
            elif key == b'\x1b':
                direction = _escape_key(fd)
                if direction is None:
                    selected = 2
                    break
                selected = ((selected if selected is not None else 0) + direction) % len(labels)
            elif key in (b'', b'\x04', b'\x03'):
                selected = 2
                break
            else:
                # Unexpected input followed by Enter must not approve by default.
                selected = None
    finally:
        # Drop any escape/paste tail before returning control to the shell.
        termios.tcsetattr(fd, termios.TCSAFLUSH, previous)
        print(flush=True)
    if selected == 1:
        print('수정 요청: 실행하지 않았습니다. 내용을 수정한 뒤 새 검토·승인이 필요합니다.')
    elif selected == 2:
        print('취소했습니다. 실행하지 않았습니다.')
    return selected == 0
