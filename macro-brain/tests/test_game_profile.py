import pytest
from src.config.game_profile import load_profile

def test_navigation_rules_payload():
    """Navigation rules should be generated from profile factions, not hardcoded."""
    profile = load_profile("profiles/default_swarm_combat.json")
    rules = profile.navigation_rules_payload()
    
    # Should have bidirectional rules for each brain-bot pair
    assert len(rules) >= 2, "Should have at least 2 navigation rules"
    
    # Verify structure
    for rule in rules:
        assert "follower_faction" in rule
        assert "target" in rule
        assert "type" in rule["target"]
        assert rule["target"]["type"] in ("Faction", "Waypoint")
    
    # Verify no hardcoded faction IDs — values should come from profile
    brain_id = profile.brain_faction.id
    bot_ids = [f.id for f in profile.bot_factions]
    follower_ids = {r["follower_faction"] for r in rules}
    assert brain_id in follower_ids, "Brain faction should be a follower"
    for bot_id in bot_ids:
        assert bot_id in follower_ids, f"Bot faction {bot_id} should be a follower"
