# roblox-robux-tracker

I got tired of manually checking if group payouts actually landed, so this polls the Roblox economy API and logs everything to a local SQLite db. I run it from cron every few hours.

## install

pip install -r requirements.txt

## usage

python track.py --cookie .ROBLOSECURITY_cookie_value

python track.py --cookie $ROBLOX_COOKIE --since 2024-01-01

The db file is created in the working directory. Use sqlite3 to query it directly.

<!-- updated: 2026-10-08 -->
