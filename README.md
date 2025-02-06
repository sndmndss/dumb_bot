## Setup



1. `python3 -m venv .venv`
2. `source .venv/bin/activate` on Mac and Linux

for windows:
`/.venv/Script/activate`

3. `pip install -r requirements.txt`
4. configure config.json

## RUN

`python main.py`


## Note for config.json

config.json:

```
{
  "public_key": "<Public_KEy>",
  "secret_key": "SECRET_KEY",
  "config_market": "",
  "order_interval_seconds": 60
}
```

config_market can be "PERP" for perps only, "SPOT" for spot only and "" for both
