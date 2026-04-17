# Task P03 Changelog – Unit Builder Nodes

## Touched Files
- [NEW] \`debug-visualizer/src/node-editor/nodes/unit.js\`
- [NEW] \`debug-visualizer/src/node-editor/nodes/stat.js\`
- [NEW] \`debug-visualizer/src/node-editor/nodes/death.js\`

## Contract Fulfillment
- Implemented \`registerUnitNode\`, \`registerStatNode\`, and \`registerDeathNode\` which export the registration logic and conform back to the Node Data Schema.
- Faction nodes can connect to Unit (\`from_faction\` / \`stats\` / \`combat\` / \`death\`).
- Included inline SVGs in each file as instructed (\`userSVG\`, \`barChartSVG\`, \`skullSVG\`).
- Handled visual and auto-assigned behaviors across all types including \`classId\` and \`statIndex\` defaults within the constraints of node creation handlers.

## Deviations/Notes
- Since the \`classId\` is auto-assigned globally, I created a module-level variable to assign it dynamically upon \`nodeCreated\` event triggering.
- The `statIndex` assignment logic is typically deferred fully to the graph compiler, but the frontend still reflects a placeholder '0'. The compiler logic must manage checking for constraints (max index 7) directly.
- Display logic requires a small delay to sync since Drawflow node data populates asynchronously during initial setup. A brief timeout applies DOM textContent.

## Human Interventions
None.
