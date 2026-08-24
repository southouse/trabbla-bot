#!/bin/bash
# .env의 토큰을 읽어 chat_id를 자동으로 채우고 테스트 메시지를 보낸다.
# 로컬 확인용. 실제 매일 발송은 GitHub Actions가 한다.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "✗ .env가 없습니다:  cp .env.example .env && open -t .env"; exit 1; }
chmod 600 .env

TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d " \"'")
[ -n "$TOKEN" ] || { echo "✗ TELEGRAM_BOT_TOKEN이 비어 있습니다."; exit 1; }

echo "→ 봇 확인 중..."
NAME=$(curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | grep -o '"username":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -n "$NAME" ] || { echo "✗ 토큰이 유효하지 않습니다."; exit 1; }
echo "  봇: @${NAME}"

CHAT=$(grep -E '^TELEGRAM_CHAT_ID=' .env | cut -d= -f2- | tr -d " \"'")
if [ -z "$CHAT" ]; then
  echo "→ chat_id 조회 중..."
  UPD=$(curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates")
  CHAT=$(printf '%s' "$UPD" | grep -o '"chat":{"id":-\?[0-9]*' | tail -1 | grep -o '\-\?[0-9]*$' || true)
  if [ -z "$CHAT" ]; then
    echo "✗ chat_id를 못 찾았습니다."
    echo "  텔레그램에서 https://t.me/${NAME} 을 열고 START를 누른 뒤 다시 실행하세요."
    exit 1
  fi
  sed -i '' "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=${CHAT}|" .env
  echo "  chat_id: ${CHAT} (.env에 기록)"
else
  echo "  chat_id: ${CHAT} (기존 값 사용)"
fi

echo "→ 테스트 발송..."
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"${CHAT}\",\"text\":\"✅ trabbla 연결 완료.\"}" \
  | grep -q '"ok":true' && echo "  전송 완료" || { echo "  ✗ 전송 실패"; exit 1; }

echo
echo "다음 두 값을 GitHub repo Secrets에 등록하세요 (Settings → Secrets and variables → Actions):"
echo "  TELEGRAM_BOT_TOKEN"
echo "  TELEGRAM_CHAT_ID = ${CHAT}"
echo
echo "gh CLI로 등록하려면:"
echo "  gh secret set TELEGRAM_BOT_TOKEN --repo southouse/trabbla-bot"
echo "  gh secret set TELEGRAM_CHAT_ID --body '${CHAT}' --repo southouse/trabbla-bot"
