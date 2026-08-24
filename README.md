# trabbla

미국 여행에서 쓰는 필수 영어를 매일 아침 **텔레그램으로** 5개씩 받는다.
문장 3개 + 응용 패턴 2개.

```
🇺🇸 미국 여행 영어 Day 1
주제: 입국심사

1. I'm here for vacation.
휴가로 왔어요.
💬 심사관: What's the purpose of your visit? → I'm here for vacation.
💡 문장을 길게 만들지 말자. "I came to travel America"처럼 말하면 오히려 어색하다.

🔁 오늘의 패턴

I'm here for ~ — ~하러 왔어요
· I'm here for vacation. 휴가로 왔어요.
· I'm here for business. 출장으로 왔어요.
· I'm here for a friend's wedding. 친구 결혼식 때문에 왔어요.
```

## 왜 이런 구조인가

내용은 **미리 만들어 큐에 쌓아두고**, 매일 발송은 GitHub Actions가 한다.

```
리필 (사람이 시킬 때)   Claude Code → queue/008.txt ... → git push
매일 아침 (자동)        GitHub Actions → 오늘 회차 파일 → 텔레그램
```

발송 시점에 LLM이 필요 없다. 그래서 **내 노트북이 꺼져 있어도, 모니터를 분리하고 뚜껑을 덮어도 온다.**
영어 문장은 오늘 만들든 한 달 전에 만들든 같기 때문에 가능한 구조다.

## 회차 계산과 따라잡기

두 값을 함께 쓴다.

| 값 | 의미 | 어디에 |
|---|---|---|
| 나가야 할 회차 | `(오늘 - START_DATE) + 1` | `config` |
| 보낸 지점 | 실제로 발송을 마친 마지막 회차 | `state/pointer.txt` |

날짜만으로는 "며칠 밀렸는지"를 알 수 있어도 "어디까지 보냈는지"를 모른다. 포인터만으로는 그 반대다.
둘의 차이가 밀린 분량이고, 실행마다 그 차이를 메꾼다.

```
정상        나가야 할 Day 5, 보낸 지점 4  →  005 발송, 포인터 5
5일 밀림    나가야 할 Day 9, 보낸 지점 4  →  005~009 발송, 포인터 9
같은 날 재실행  나가야 할 Day 5, 보낸 지점 5  →  보낼 것 없음
```

**Actions가 며칠 건너뛰어도 그 회차가 유실되지 않는다.** 다음 실행이 밀린 만큼 따라잡는다.
같은 날 두 번 돌아도 중복 발송되지 않는다.

한 번에 몰아 보내는 상한은 `config`의 `CATCHUP_MAX`(기본 5)다. 30일이 밀렸다면 하루 5개씩
엿새에 걸쳐 소진된다. 한 번에 전부 받고 싶으면 `CATCHUP_MAX=0`으로 두면 되지만,
텔레그램에 수십 개가 한꺼번에 쏟아진다.

포인터가 바뀌면 Actions가 `state/pointer.txt`를 repo에 커밋한다. 그래서 워크플로에
`contents: write` 권한이 필요하다.

## 구성

| 파일 | 역할 |
|---|---|
| `queue/NNN.txt` | 발송 대기 중인 완성된 메시지. 파일 하나가 하루치 |
| `config` | `START_DATE`(001번을 보내는 날), `CATCHUP_MAX`(한 번에 보낼 상한) |
| `state/pointer.txt` | 어디까지 보냈는지. Actions가 갱신하고 커밋한다 |
| `topics.csv` | 상황별 주제 20개. 회차마다 순서대로 돌고 끝나면 처음으로 |
| `sent.tsv` | 이미 쓴 문장·패턴 기록. 리필할 때 중복 회피용 |
| `send_next.py` | 오늘 회차를 발송. 표준 라이브러리만 사용 |
| `status.py` | 재고, 다음 회차·주제, 이미 쓴 문장 목록 출력 |
| `finish_setup.sh` | 로컬에서 봇 검증 + chat_id 조회 |
| `.github/workflows/daily.yml` | 매일 23:21 UTC (= 08:21 KST) 발송 |

Python 표준 라이브러리만 쓴다. venv도 pip 설치도 없다.

## 설치

### 1. 텔레그램 봇

`@BotFather` → `/newbot` → 표시 이름과 username 정하고 토큰 받기.
그 다음 **텔레그램에서 봇을 찾아 START를 누른다.** 이걸 빠뜨리면 chat_id를 알 수 없다.

### 2. chat_id 확인

```bash
cp .env.example .env && open -t .env    # 토큰만 붙여넣고 저장
./finish_setup.sh
```

chat_id를 자동으로 찾아 `.env`에 기록하고 테스트 메시지를 보낸다.
`.env`는 로컬 확인용이며 git에 올라가지 않는다.

### 3. GitHub repo와 Secrets

```bash
gh repo create trabbla-bot --private --source=. --push
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
```

`gh secret set`은 값을 물어본다. 토큰을 커밋이나 채팅에 붙여넣지 말고 여기서 직접 입력한다.

### 4. 확인

repo의 Actions 탭 → `daily-phrase` → **Run workflow**로 즉시 한 번 돌려본다.
텔레그램에 오면 끝이다.

## 사용법

| 명령 | 내용 |
|---|---|
| `/phrase` | 재고와 오늘 회차 확인, 원하면 즉시 발송 |
| `/phrase-refill 14` | 큐를 14일치 더 채우고 푸시 (기본 7) |
| `./status.py` | 재고와 다음 회차 확인 |
| `./send_next.py --dry-run` | 오늘 나갈 내용 미리보기 |

재고가 7일치 이하로 떨어지면 그날 메시지 끝에 알림이 붙는다. 다 떨어지면 재고 소진 안내가 온다.

## 커스터마이즈

**주제 순서** — `topics.csv`를 고친다. 여행이 임박하면 입국심사·공항을 위로 올린다.
단 이미 만들어둔 큐 파일에는 소급되지 않는다.

**시작일 변경** — `config`의 `START_DATE`. 큐 파일 번호와 날짜의 대응이 한꺼번에 밀린다.
이미 발송한 뒤 START_DATE를 앞으로 당기면 밀린 분량으로 인식되어 몰아서 나갈 수 있으니
`state/pointer.txt`도 함께 맞춰야 한다.

**형식·난이도** — `.claude/commands/phrase-refill.md`를 고친 뒤 다시 리필한다.
이미 큐에 있는 파일은 그대로이므로, 형식을 바꾸려면 해당 파일을 지우고 다시 만든다.

**복습** — `sent.tsv`가 그대로 학습 기록이다.
```bash
column -t -s $'\t' sent.tsv | less
```

## 한계

**GitHub Actions 스케줄은 정시를 보장하지 않는다.** 혼잡할 때 수 분에서 수십 분 늦고,
드물게 건너뛴다. 다만 포인터가 남아 있어 회차 자체는 유실되지 않고 다음 실행이 따라잡는다.

**활동이 없는 repo는 스케줄 워크플로가 중단된다.** 리필할 때마다 커밋이 생기므로
정기적으로 채우면 문제되지 않는다.

**재고 관리가 필요하다.** 큐가 비면 학습이 멈춘다. 소진 경고가 오면 리필한다.
