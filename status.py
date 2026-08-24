#!/usr/bin/env python3
"""큐 재고와 다음에 만들 회차·주제, 그리고 이미 쓴 문장 목록을 출력한다.

리필(/phrase-refill)할 때 이 출력을 근거로 다음 파일을 만든다.
"""
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).parent
QUEUE = BASE / "queue"


def topics():
    rows = []
    for raw in (BASE / "topics.csv").read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#"):
            rows.append(raw)
    return rows


def start_date():
    for raw in (BASE / "config").read_text(encoding="utf-8").splitlines():
        if raw.strip().startswith("START_DATE="):
            return date.fromisoformat(raw.split("=", 1)[1].strip())
    sys.exit("config에 START_DATE가 없습니다.")


def main():
    sd = start_date()
    today = date.today()
    cur = (today - sd).days + 1
    items = sorted(int(p.stem) for p in QUEUE.glob("[0-9][0-9][0-9].txt"))
    tps = topics()

    print(f"오늘: {today}   START_DATE: {sd}   현재 회차: Day {cur}")
    if not items:
        print("큐 비어 있음. 001부터 만들어야 한다.")
        nxt = 1
    else:
        last = items[-1]
        print(f"큐: {items[0]:03d} ~ {last:03d} ({len(items)}개)")
        gaps = [n for n in range(1, last + 1) if n not in items]
        if gaps:
            print(f"⚠️ 빠진 회차: {', '.join(f'{g:03d}' for g in gaps)}")
        remaining = len([n for n in items if n >= cur])
        print(f"남은 재고: {remaining}일치 (마지막 {last:03d}는 {sd + timedelta(days=last - 1)}에 발송)")
        nxt = last + 1

    print(f"\n다음에 만들 파일: {nxt:03d}.txt")
    print(f"주제: {tps[(nxt - 1) % len(tps)]}   (전체 {len(tps)}개 중 {((nxt - 1) % len(tps)) + 1}번째)")
    if nxt > len(tps):
        print(f"※ 주제가 한 바퀴 돌았다. 같은 주제지만 이미 쓴 문장과 겹치지 않게 새로 만들 것.")

    path = BASE / "sent.tsv"
    rows = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.reader(f, delimiter="\t")
            next(r, None)
            rows = [x for x in r if len(x) >= 3]
    print(f"\n=== 이미 쓴 문장·패턴 {len(rows)}건 (절대 다시 쓰지 말 것) ===")
    for _, t, e in [(x[0], x[1], x[2]) for x in rows]:
        print(f"[{t}] {e}")


if __name__ == "__main__":
    main()
