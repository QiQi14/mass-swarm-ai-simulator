# ZMQ Protocol & Directives

## 1. ZMQ Communication Model

**Pattern:** REQ/REP over TCP (`tcp://127.0.0.1:5555`)

```
Python (REQ)                    Rust (REP)
    |                               |
    |--- macro_directives --------->|  (Python sends commands)
    |                               |  Rust simulates N ticks
    |<-- state_snapshot ------------|  (Rust sends new state)
    |                               |
    (repeat every ai_eval_interval_ticks)
```

- Python is the REQ client, Rust is the REP server
- Each exchange: Python sends directives → Rust simulates → Rust replies with snapshot
- Exchange rate: every `ai_eval_interval_ticks` (default: 30 ticks = 0.5 seconds at 60 TPS)

---