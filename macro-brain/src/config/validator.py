"""Profile Validator — Ensures a GameProfile is structurally sound and logically correct.

Rule Checks:
  V1: Faction ID uniqueness — no duplicates in factions[].id (Error)
  V2: Exactly one faction with role == "brain" (Error)
  V3: At least one faction with role == "bot" (Error)
  V4: Combat rule faction IDs exist in factions[].id (Error)
  V5: Action indices 0..N-1 contiguous, no gaps (Error)
  V6: Curriculum stages sequential (1, 2, 3, ...) (Error)
  V7: Graduation action_usage keys match action names (Warning)
  V8: No action unlock_stage exceeds max curriculum stage (Warning)
  V9: cell_size * grid_width ≈ width (within 10% tolerance) (Warning)
"""

import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path

from src.config.game_profile import GameProfile, load_profile


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_profile(profile: GameProfile) -> ValidationResult:
    errors = []
    warnings = []

    # V1: Faction ID uniqueness
    faction_ids = [f.id for f in profile.factions]
    unique_ids = set(faction_ids)
    if len(faction_ids) != len(unique_ids):
        errors.append("V1: Faction IDs are not unique.")

    # V2: Exactly one faction with role == "brain"
    brain_count = sum(1 for f in profile.factions if f.role == "brain")
    if brain_count != 1:
        errors.append(f"V2: Expected exactly 1 brain faction, found {brain_count}.")

    # V3: At least one faction with role == "bot"
    bot_count = sum(1 for f in profile.factions if f.role == "bot")
    if bot_count < 1:
        errors.append("V3: Expected at least 1 bot faction.")

    # V4: Combat rule faction IDs exist
    for rule in profile.combat.rules:
        if rule.source_faction not in unique_ids:
            errors.append(f"V4: Combat rule source faction {rule.source_faction} not found.")
        if rule.target_faction not in unique_ids:
            errors.append(f"V4: Combat rule target faction {rule.target_faction} not found.")

    # V5: Action indices 0..N-1 contiguous
    action_indices = sorted(a.index for a in profile.actions)
    expected_indices = list(range(len(profile.actions)))
    if action_indices != expected_indices:
        errors.append("V5: Action indices are not contiguous from 0 to N-1.")

    # V6: Curriculum stages sequential
    stages = [s.stage for s in profile.training.curriculum]
    expected_stages = list(range(1, len(stages) + 1))
    if stages != expected_stages:
        errors.append("V6: Curriculum stages are not sequential starting from 1.")

    # V7: Graduation action_usage keys match action names
    action_names = {a.name for a in profile.actions}
    for stage_config in profile.training.curriculum:
        if stage_config.graduation and stage_config.graduation.action_usage:
            for key in stage_config.graduation.action_usage:
                if key not in action_names:
                    warnings.append(f"V7: Graduation action_usage key '{key}' in stage {stage_config.stage} does not match any action name.")

    # V8: No action unlock_stage exceeds max curriculum stage
    max_stage = max(stages) if stages else 0
    for action in profile.actions:
        if action.unlock_stage > max_stage:
            warnings.append(f"V8: Action '{action.name}' unlock_stage ({action.unlock_stage}) exceeds max curriculum stage ({max_stage}).")

    # V9: cell_size * grid_width ≈ width (within 10% tolerance)
    grid_width = profile.world.grid_width
    cell_size = profile.world.cell_size
    width = profile.world.width
    if not (0.9 * width <= grid_width * cell_size <= 1.1 * width):
        warnings.append(f"V9: cell_size ({cell_size}) * grid_width ({grid_width}) does not closely match world width ({width}).")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def main():
    parser = argparse.ArgumentParser(description="Validate GameProfile structure.")
    parser.add_argument("profile_path", type=str, help="Path to profile JSON")
    args = parser.parse_args()

    try:
        profile = load_profile(args.profile_path)
    except Exception as e:
        print(f"❌ Failed to load profile: {e}")
        sys.exit(1)

    print(f"📋 Validating: {profile.meta.name} v{profile.meta.version}")
    result = validate_profile(profile)

    checks = [
        ("V1", "Faction IDs unique"),
        ("V2", "Brain faction found"),
        ("V3", "Bot factions found"),
        ("V4", "Combat rules reference valid factions"),
        ("V5", "Action indices contiguous"),
        ("V6", "Curriculum stages sequential"),
        ("V7", "Graduation action keys valid"),
        ("V8", "Unlock stages within bounds"),
        ("V9", "Grid dimensions consistent")
    ]

    for code, success_msg in checks:
        if any(e.startswith(code) for e in result.errors):
            msg = next((e for e in result.errors if e.startswith(code)), "Error")
            print(f"  ❌ {msg}")
        elif any(w.startswith(code) for w in result.warnings):
            msg = next((w for w in result.warnings if w.startswith(code)), "Warning")
            print(f"  ⚠️  {msg}")
        else:
            if code == "V2":
                brain_id = next((f.id for f in profile.factions if f.role == "brain"), 0)
                print(f"  ✅ V2: Brain faction found (id={brain_id})")
            elif code == "V3":
                bot_count = sum(1 for f in profile.factions if f.role == "bot")
                print(f"  ✅ V3: Bot factions found ({bot_count})")
            elif code == "V5":
                if profile.actions:
                    max_idx = max(a.index for a in profile.actions)
                    print(f"  ✅ V5: Action indices contiguous (0-{max_idx})")
                else:
                    print(f"  ✅ V5: Action indices contiguous (none)")
            elif code == "V6":
                if profile.training.curriculum:
                    max_stage = max(s.stage for s in profile.training.curriculum)
                    print(f"  ✅ V6: Curriculum stages sequential (1-{max_stage})")
                else:
                    print(f"  ✅ V6: Curriculum stages sequential (none)")
            else:
                print(f"  ✅ {code}: {success_msg}")

    if result.valid:
        print(f"✅ Profile valid ({len(result.errors)} errors, {len(result.warnings)} warnings)")
    else:
        print(f"❌ Profile invalid ({len(result.errors)} errors, {len(result.warnings)} warnings)")
        sys.exit(1)


if __name__ == "__main__":
    main()
