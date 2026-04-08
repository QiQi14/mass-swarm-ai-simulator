# Task C2: Launch Script Changelog

## Touched Files
- `train.sh` (Created)

## Contract Fulfillment
- Wrote the `train.sh` Bash script to properly proxy executions between `micro-core`, `macro-brain`, and `debug-visualizer`.
- Correctly parsed the user CLI params for `--profile`, `--timesteps` and `--no-visualizer`, passing all unrecognized arbitrary tags directly to the python training endpoint.
- Correctly added wait loops leveraging `lsof` for the `micro-core` initializations blocking dependencies appropriately.
- Instantiated the cleanup trap block ensuring processes are aborted during standard INT or TERM signal exits, terminating Rust dynamically regardless of parallel job behavior.
- Executed file permission operations formatting `train.sh` to executable standard using `chmod +x train.sh`.

## Deviations/Notes
- **Bug Fix**: The original task spec required an active `lsof` loop wait specifically parsing for ZMQ port `5555`. Because `micro-core` does NOT bind port `5555`, but connects to it, the `lsof -i :5555` call evaluated forever before entering the Python block (the app actually creating the port connection) producing a 30s crash deadlock. 
As per Rule 4, I analyzed this limitation and dropped this deadlock check. As `micro-core` binds `8080`, performing the loop block directly against `8080` safely assures initialization confirmation to trigger the Python block efficiently.

## Human Interventions
- None
