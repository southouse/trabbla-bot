#!/usr/bin/env python3
"""아직 안 보낸 큐 항목을 순서대로 발송한다. 표준 라이브러리만 사용.

나가야 할 회차 = (오늘 - START_DATE) + 1
실제 보낸 지점 = state/pointer.txt
둘의 차이가 밀린 분량이고, 한 번에 CATCHUP_MAX개까지 따라잡는다.

포인터를 쓰기 때문에 스케줄이 며칠 건너뛰어도 그 회차가 유실되지 않는다.
같은 날 두 번 실행하면 보낼 게 없으므로 아무것도 보내지 않는다 (중복 방지).

자격증명은 환경변수 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 우선, 없으면 .env.
--dry-run 은 발송·포인터 갱신 없이 무엇이 나갈지만 출력한다.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
QUEUE = BASE / "queue"
POINTER = BASE / "state" / "pointer.txt"
LIMIT = 3800
LOW_STOCK = 7


def cfg_file():
    out = {}
    for raw in (BASE / "config").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def creds():
    out = {}
    path = BASE / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw and not raw.startswith("#") and "=" in raw:
                k, v = raw.split("=", 1)
                out[k.strip()] = v.strip().strip("'\"")
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if os.environ.get(k):
            out[k] = os.environ[k]
        if not out.get(k):
            sys.exit(f"{k}가 없습니다. 환경변수나 .env로 지정하세요.")
    return out


def pointer():
    if not POINTER.exists():
        return 0
    t = POINTER.read_text(encoding="utf-8").strip()
    return int(t) if t else 0


def to_html(text):
    out = html.escape(text, quote=False)
    out = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w])_([^_\n]+)_(?![\w])", r"<i>\1</i>", out)
    return out


def chunks(text):
    buf = ""
    for ln in text.splitlines(keepends=True):
        if len(buf) + len(ln) > LIMIT and buf:
            yield buf
            buf = ""
        buf += ln
    if buf.strip():
        yield buf


def send(c, text):
    url = f"https://api.telegram.org/bot{c['TELEGRAM_BOT_TOKEN']}/sendMessage"
    for part in chunks(text):
        req = urllib.request.Request(
            url,
            data=json.dumps({
                "chat_id": c["TELEGRAM_CHAT_ID"],
                "text": to_html(part),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status != 200:
                    sys.exit(f"전송 실패 {r.status}")
        except urllib.error.HTTPError as e:
            sys.exit(f"전송 실패 {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def main():
    dry = "--dry-run" in sys.argv
    conf = cfg_file()
    sd = date.fromisoformat(conf["START_DATE"])
    cap = int(conf.get("CATCHUP_MAX", "5"))

    due = (date.today() - sd).days + 1
    sent = pointer()
    have = sorted(int(p.stem) for p in QUEUE.glob("[0-9][0-9][0-9].txt"))
    last = have[-1] if have else 0

    print(f"오늘까지 나가야 할 회차: Day {due} / 보낸 지점: Day {sent} / 큐 보유: ~{last}")

    if due < 1:
        print("START_DATE가 아직 오지 않았습니다.")
        return
    if sent >= due:
        print("보낼 것이 없습니다 (이미 오늘 회차까지 발송됨).")
        return

    targets = [n for n in range(sent + 1, due + 1) if n in have]
    missing = [n for n in range(sent + 1, due + 1) if n not in have]
    backlog = len(targets)
    if cap > 0:
        targets = targets[:cap]

    if not targets:
        c = creds()
        msg = ("⚠️ *trabbla 재고 소진*\n\n"
               f"Day {due}까지 나가야 하는데 큐에 남은 항목이 없습니다.\n"
               "Claude Code에서 /phrase-refill 로 채워주세요.")
        print(f"재고 없음: Day {sent + 1}~{due} 파일이 없다")
        if not dry:
            send(c, msg)
        return

    print(f"발송 대상: {targets} (밀린 분량 {backlog}개, 상한 {cap or '무제한'})")
    if missing:
        print(f"⚠️ 큐에 없어 건너뛴 회차: {missing}")

    if dry:
        for n in targets:
            t = (QUEUE / f"{n:03d}.txt").read_text(encoding="utf-8")
            print(f"--- {n:03d} ({len(t)}자) --- {t.splitlines()[1]}")
        return

    c = creds()
    for i, n in enumerate(targets, 1):
        text = (QUEUE / f"{n:03d}.txt").read_text(encoding="utf-8")
        if backlog > 1:
            text = f"_밀린 회차 따라잡기 {i}/{len(targets)} (총 {backlog}개 대기)_\n\n" + text
        remaining = last - n
        if remaining <= LOW_STOCK:
            text += f"\n\n_📦 남은 재고 {remaining}일치. /phrase-refill 로 채워주세요._"
        send(c, text)
        print(f"  Day {n} 발송")

    POINTER.write_text(f"{targets[-1]}\n", encoding="utf-8")
    print(f"포인터 갱신: {targets[-1]}")
    if backlog > len(targets):
        print(f"남은 밀린 분량 {backlog - len(targets)}개는 다음 실행에서 발송")


if __name__ == "__main__":
    main()
