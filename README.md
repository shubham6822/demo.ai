# demo.ai

Company assistant agent for demos: load any company's PDF with one command, then chat with an agent that answers only about that company.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # add your GOOGLE_API_KEY (https://aistudio.google.com/apikey)

.venv/bin/python -m app.ingest --company "Company X" companyx.pdf
.venv/bin/python -m app.chat
```

Run `ingest` again with another company's PDF to switch. See [docs/PROJECT-CONTEXT.md](docs/PROJECT-CONTEXT.md).
