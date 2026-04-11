# Lesson: Mocking Environments for SB3 Callbacks in pytest

**Category:** gotcha
**Discovered:** task_08_training_callbacks (2026-04-10)
**Severity:** low

## Context
When writing unit tests for stable_baselines3 (SB3) custom Callbacks using pytest.

## Problem
Attempting to directly set `cb.training_env = DummyEnv()` fails with `AttributeError` because `training_env` is a property that points to `self.model.get_env()`. Setting it directly is disallowed.

## Correct Approach
Instantiate a dummy model that implements `get_env()`, and call `cb.init_callback(model)`. This safely wires the environment without triggering property setter exceptions.

## Example
- ❌ What the executor/QA did: 
```python
cb = EpisodeLogCallback(log_path=log_path)
cb.training_env = DummyTrainingEnv()
cb._on_training_start()
```

- ✅ What it should be: 
```python
class DummyModel:
    def __init__(self):
        self.env = DummyTrainingEnv()
    def get_env(self):
        return self.env

cb = EpisodeLogCallback(log_path=log_path)
cb.init_callback(DummyModel())
cb._on_training_start()
```
