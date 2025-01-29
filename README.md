# YHSTBOT - Yüksek Hızlı Tren Telegram Botu - TCDD HIZLI TREN BOT - YHT Bot

export BOT_TOKEN and AUTH_USER_IDS environment variables before starting docker compose.

`export BOT_TOKEN=<telegram_bot_token>`

`export AUTH_USER_IDS=1234567,1234567,123467 # comma delimited allowed user ids.`

docker compose up -d

@YHSTBOT user at telegram
/start for starting conversation with bot

## Inline Functions

"@YHSTBOT query pendik ankara 17ekim15:30" for setting the start trip for search
"@YHSTBOT stations" for listing avaliable YHT stations

