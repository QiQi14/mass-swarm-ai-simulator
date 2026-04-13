# Feature 1: Python Config Extensions (Task 01)

## Purpose

Add `aoe` and `penetration` support to the Python-side config dataclasses so that `_build_combat_rule()` can serialize AoE/penetration configs to the Rust-compatible JSON format.

**Currently:** `CombatRuleConfig` has no `aoe` or `penetration` fields. The Rust side accepts these via `serde(default)`, but Python has never sent them.

---

## Target Files

- `macro-brain/src/config/definitions.py`
- `macro-brain/src/config/parser.py`  
- `macro-brain/src/config/game_profile.py`

## Dependencies

None (Phase 1 — no external dependencies)

## Context Bindings

- `context/engine` (for Rust AoE/Penetration struct contracts)
- `context/training`

---

## Strict Instructions

### Step 1: Add AoE + Penetration Dataclasses to `definitions.py`

After the `CombatRuleConfig` class (~line 72), add these new dataclasses:

```python
# ── AoE Configuration ──────────────────────────────────────────────

@dataclass(frozen=True)
class AoeShapeDef:
    """AoE damage shape. type must be 'Circle', 'Ellipse', or 'ConvexPolygon'.
    
    Matches Rust AoeShape enum with serde(tag='type').
    """
    type: str  # "Circle", "Ellipse", "ConvexPolygon"
    # Circle fields
    radius: float | None = None
    # Ellipse fields
    semi_major: float | None = None
    semi_minor: float | None = None
    # ConvexPolygon fields — list of [dx, dy] offsets, CCW wound
    vertices: list[list[float]] | None = None
    # Rotation (for Ellipse/ConvexPolygon)
    rotation_mode: str | None = None  # "TargetAligned" or {"Fixed": angle}

    def to_dict(self) -> dict:
        d: dict = {"type": self.type}
        if self.type == "Circle":
            d["radius"] = self.radius
        elif self.type == "Ellipse":
            d["semi_major"] = self.semi_major
            d["semi_minor"] = self.semi_minor
            if self.rotation_mode:
                d["rotation_mode"] = self.rotation_mode
        elif self.type == "ConvexPolygon":
            d["vertices"] = self.vertices
            if self.rotation_mode:
                d["rotation_mode"] = self.rotation_mode
        return d


@dataclass(frozen=True)
class AoeConfigDef:
    """AoE damage area configuration.
    
    Matches Rust AoeConfig struct.
    """
    shape: AoeShapeDef
    falloff: str  # "None", "Linear", "Quadratic"

    def to_dict(self) -> dict:
        return {
            "shape": self.shape.to_dict(),
            "falloff": self.falloff,
        }


@dataclass(frozen=True)
class EnergyModelDef:
    """Penetration energy model. Matches Rust EnergyModel enum.
    
    type must be 'Kinetic' or 'Beam'.
    """
    type: str  # "Kinetic" or "Beam"
    base_energy: float | None = None  # Only for Kinetic

    def to_dict(self) -> dict:
        if self.type == "Kinetic":
            return {"Kinetic": {"base_energy": self.base_energy}}
        return "Beam"


@dataclass(frozen=True)
class PenetrationConfigDef:
    """Penetration (piercing) damage configuration.
    
    Matches Rust PenetrationConfig struct.
    """
    ray_width: float
    energy_model: EnergyModelDef
    absorption_stat_index: int
    absorption_ignores_mitigation: bool = True
    max_targets: int | None = None

    def to_dict(self) -> dict:
        d = {
            "ray_width": self.ray_width,
            "energy_model": self.energy_model.to_dict(),
            "absorption_stat_index": self.absorption_stat_index,
            "absorption_ignores_mitigation": self.absorption_ignores_mitigation,
        }
        if self.max_targets is not None:
            d["max_targets"] = self.max_targets
        return d
```

### Step 2: Add `aoe` and `penetration` fields to `CombatRuleConfig`

Add two new optional fields **after** `cooldown_ticks`:

```python
@dataclass(frozen=True)
class CombatRuleConfig:
    source_faction: int
    target_faction: int
    range: float
    effects: list[StatEffectConfig]
    source_class: int | None = None
    target_class: int | None = None
    range_stat_index: int | None = None
    mitigation: MitigationConfig | None = None
    cooldown_ticks: int | None = None
    aoe: AoeConfigDef | None = None             # ← NEW
    penetration: PenetrationConfigDef | None = None  # ← NEW
```

### Step 3: Update `_build_combat_rule()` in `game_profile.py`

Add serialization for the new fields at the end of the method, after the `cooldown_ticks` block:

```python
if rule.aoe is not None:
    payload["aoe"] = rule.aoe.to_dict()
if rule.penetration is not None:
    payload["penetration"] = rule.penetration.to_dict()
```

### Step 4: Update `_parse_combat_rule()` in `parser.py`

Add parsing of `aoe` and `penetration` from raw JSON:

```python
def _parse_combat_rule(raw_rule: dict) -> CombatRuleConfig:
    # ... existing mitigation parsing ...
    
    # Parse AoE config
    aoe_raw = raw_rule.get("aoe")
    aoe = None
    if aoe_raw:
        shape_raw = aoe_raw["shape"]
        shape = AoeShapeDef(
            type=shape_raw["type"],
            radius=shape_raw.get("radius"),
            semi_major=shape_raw.get("semi_major"),
            semi_minor=shape_raw.get("semi_minor"),
            vertices=shape_raw.get("vertices"),
            rotation_mode=shape_raw.get("rotation_mode"),
        )
        aoe = AoeConfigDef(shape=shape, falloff=aoe_raw["falloff"])
    
    # Parse Penetration config
    pen_raw = raw_rule.get("penetration")
    penetration = None
    if pen_raw:
        em_raw = pen_raw["energy_model"]
        if isinstance(em_raw, dict):
            if "Kinetic" in em_raw:
                energy_model = EnergyModelDef(type="Kinetic", base_energy=em_raw["Kinetic"]["base_energy"])
            else:
                energy_model = EnergyModelDef(type="Beam")
        elif em_raw == "Beam":
            energy_model = EnergyModelDef(type="Beam")
        else:
            energy_model = EnergyModelDef(type="Beam")
        penetration = PenetrationConfigDef(
            ray_width=pen_raw["ray_width"],
            energy_model=energy_model,
            absorption_stat_index=pen_raw["absorption_stat_index"],
            absorption_ignores_mitigation=pen_raw.get("absorption_ignores_mitigation", True),
            max_targets=pen_raw.get("max_targets"),
        )
    
    return CombatRuleConfig(
        # ... existing fields ...
        aoe=aoe,
        penetration=penetration,
    )
```

> [!WARNING]
> **Import order:** `parser.py` must import the new classes: `AoeShapeDef`, `AoeConfigDef`, `EnergyModelDef`, `PenetrationConfigDef` from `definitions.py`.

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: Python / pytest
  Acceptance_Criteria:
    - "CombatRuleConfig with aoe=None serializes identically to current (backward compat)"
    - "CombatRuleConfig with AoE Circle shape serializes to valid Rust JSON"
    - "CombatRuleConfig with ConvexPolygon + TargetAligned serializes correctly"
    - "CombatRuleConfig with Kinetic penetration serializes with energy_model dict"
    - "CombatRuleConfig with Beam penetration serializes energy_model as string"
    - "Parser roundtrip: build → to_dict → parse → to_dict produces identical output"
  Suggested_Test_Commands:
    - "cd macro-brain && .venv/bin/python -m pytest tests/test_stage_combat_rules.py -v"
```
