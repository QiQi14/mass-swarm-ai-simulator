import re

with open("micro-core/src/systems/interaction.rs", "r") as f:
    content = f.read()

# The script appended tests outside. 
# It replaced "}\n}" with "}\n" + new_tests_block + "\n}"
# The original end was:
#        assert_eq!(stat.0[0], 100.0); // No self-harm
#    }
#}
# Now it is:
#        assert_eq!(stat.0[0], 100.0); // No self-harm
#    }
#
#    #[test]
# ... new tests ...
# }
# } (Wait, I replaced `}\n}`  which means the last `}` of `mod tests` was left, then tests, then `}`.
#  Actually, `}\n}` matches the end of `test_self_interaction_prevented` and the `mod tests` end.

# Let's extract the new tests out of the unexpected place.
# Find where the `test_class_filtering_source` starts
idx = content.find("    #[test]\n    fn test_class_filtering_source()")
if idx != -1:
    new_tests = content[idx:-2] # everything from here to the end except the final brace
    part1 = content[:idx] # everything before
    
    # We want to put new_tests BEFORE the final `}`
    # Wait, part1 ends with `    }\n` or similar. Let's make sure we're inside mod tests.
    
    # We can just rebuild the whole test part or file easily.
    # Actually just strip the trailing braces from part1, and put new_tests out.
    part1_clean = part1.rstrip()
    if part1_clean.endswith("}"):
        part1_clean = part1_clean[:-1].rstrip()
    
    new_content = part1_clean + "\n\n" + new_tests + "\n}\n"
    
    with open("micro-core/src/systems/interaction.rs", "w") as f:
        f.write(new_content)
