import { getPreset } from '../controls/algorithm-test.js';
import { getNodeHTML } from './drawflow-setup.js';
import { startBrainRunner } from './brain-runner.js';
import { uploadedModels } from './nodes/general.js';

let activeBrainRunners = [];


/**
 * Compile the current node graph into WS commands.
 * @param {Drawflow} editor - The Drawflow editor instance
 * @returns {object} - CompiledScenario
 */
export function compileGraph(editor) {
    const exportData = editor.export();
    const nodes = exportData.drawflow?.Home?.data || {};

    const spawns = [];
    const navigation = { rules: [] };
    const interaction = { rules: [] };
    const removal = { rules: [] };
    const aggro = [];
    const brains = [];
    const errors = [];

    const factions = [];
    const units = [];
    const stats = [];
    const combats = [];
    const navigations = [];
    const waypoints = [];
    const deaths = [];
    const relationships = [];
    const movements = [];
    const generals = [];

    const nodeMap = new Map();

    for (const id in nodes) {
        const node = nodes[id];
        nodeMap.set(String(id), node);
        
        switch (node.name) {
            case 'faction': factions.push(node); break;
            case 'unit': units.push(node); break;
            case 'stat': stats.push(node); break;
            case 'combat': combats.push(node); break;
            case 'navigation': navigations.push(node); break;
            case 'waypoint': waypoints.push(node); break;
            case 'death': deaths.push(node); break;
            case 'relationship': relationships.push(node); break;
            case 'movement': movements.push(node); break;
            case 'general': generals.push(node); break;
        }
    }

    if (factions.length === 0) {
        errors.push('No faction nodes found');
    }

    const getConnectedNodesFromOutput = (node, portName) => {
        const connections = node.outputs[portName]?.connections || [];
        return connections.map(conn => nodeMap.get(String(conn.node)));
    };

    const getConnectedNodesFromInput = (node, portName) => {
        const connections = node.inputs[portName]?.connections || [];
        return connections.map(conn => nodeMap.get(String(conn.node)));
    };

    const factionsWithGeneral = new Set();
    for (const f of factions) {
        if (getConnectedNodesFromOutput(f, 'general').length > 0) {
            factionsWithGeneral.add(parseInt(f.data.factionId, 10));
        }
    }

    for (const faction of factions) {
        const factionId = parseInt(faction.data.factionId, 10) || 0;
        
        const connectedUnits = getConnectedNodesFromOutput(faction, 'units');
        if (connectedUnits.length === 0) {
            errors.push(`Faction '${faction.data.name}' has no Unit connected.`);
        }

        const connectedGenerals = getConnectedNodesFromOutput(faction, 'general');
        for (const gen of connectedGenerals) {
            const nodeId = String(gen.id);
            brains.push({
                factionId: factionId,
                modelPath: gen.data.modelPath || '',
                modelBlob: uploadedModels.get(nodeId) || null,
                decisionInterval: parseInt(gen.data.decisionInterval, 10) || 30,
                mode: gen.data.mode || 'rust'
            });
        }

        for (const unit of connectedUnits) {
            const classId = parseInt(unit.data.classId, 10) || 0;

            let movementConfig = undefined;
            for (const mov of movements) {
                const navInputs = mov.inputs.unit?.connections || [];
                for (const c of navInputs) {
                    if (String(c.node) === String(unit.id)) {
                        movementConfig = {
                            speedPreset: mov.data.speedPreset || 'normal',
                            maxSpeed: parseFloat(mov.data.maxSpeed) || 100,
                            steeringFactor: parseFloat(mov.data.steeringFactor) || 1.0,
                            separationRadius: parseFloat(mov.data.separationRadius) || 10,
                            engagementRange: parseFloat(mov.data.engagementRange) || 15
                        };
                        break;
                    }
                }
                if (movementConfig) break;
            }

            const uStats = getConnectedNodesFromInput(unit, 'stats');
            if (uStats.length === 0) {
                errors.push(`Unit '${unit.data.unitName}' has no Stat nodes connected.`);
            }

            const usedStatIndices = new Set();
            const statsArray = [];
            for (const st of uStats) {
                const index = parseInt(st.data.statIndex, 10);
                if (usedStatIndices.has(index)) {
                    errors.push(`Unit '${unit.data.unitName}' has duplicate stat index ${index} attached.`);
                }
                usedStatIndices.add(index);
                statsArray.push({ index, value: parseFloat(st.data.initialValue) || 0 });
            }

            spawns.push({
                faction_id: factionId,
                amount: parseInt(faction.data.spawnCount, 10) || 0,
                x: parseFloat(faction.data.spawnX) || 0,
                y: parseFloat(faction.data.spawnY) || 0,
                spread: parseFloat(faction.data.spawnSpread) || 0,
                stats: statsArray,
                ...(movementConfig ? { movement_config: movementConfig } : {})
            });

            const uDeath = getConnectedNodesFromInput(unit, 'death');
            if (uDeath.length === 0) {
                console.warn(`Unit '${unit.data.unitName}' should have a Death node connected.`);
            }
        }
    }

    for (const combat of combats) {
        let attackers = getConnectedNodesFromInput(combat, 'attacker');
        if (attackers.length === 0) attackers = getConnectedNodesFromInput(combat, 'input_1');
        
        let targets = getConnectedNodesFromInput(combat, 'target');
        if (targets.length === 0) targets = getConnectedNodesFromInput(combat, 'input_2');
        
        let damageStats = getConnectedNodesFromInput(combat, 'damage_stat');
        if (damageStats.length === 0) damageStats = getConnectedNodesFromInput(combat, 'input_3');

        if (attackers.length === 0 || targets.length === 0) continue;

        const attackerNode = attackers[0];
        const targetNode = targets[0];

        const getFactionOfUnitOrNode = (n) => {
            if (n.name === 'faction') return parseInt(n.data.factionId, 10);
            if (n.name === 'unit') {
                let facts = getConnectedNodesFromInput(n, 'from_faction');
                if (facts.length === 0) facts = getConnectedNodesFromInput(n, 'input_1');
                if (facts.length > 0) return parseInt(facts[0].data.factionId, 10);
            }
            return 0;
        };

        const getClassOfUnitOrNode = (n) => {
            if (n && n.name === 'unit' && n.data.classId !== undefined) {
                return parseInt(n.data.classId, 10);
            }
            return null;
        };

        const sourceFactionId = getFactionOfUnitOrNode(attackerNode);
        const targetFactionId = getFactionOfUnitOrNode(targetNode);

        let statIndex = 0;
        if (damageStats.length > 0) {
            statIndex = parseInt(damageStats[0].data.statIndex, 10);
        }

        const sourceClass = getClassOfUnitOrNode(attackerNode);
        const targetClass = getClassOfUnitOrNode(targetNode);

        const rule = {
            source_faction: sourceFactionId,
            target_faction: targetFactionId,
            range: parseFloat(combat.data.range) || 0,
            effects: [{
                stat_index: statIndex,
                delta_per_second: parseFloat(combat.data.damage) || 0
            }],
            cooldown_ticks: parseInt(combat.data.cooldownTicks, 10) || 0
        };

        if (sourceClass !== null && !isNaN(sourceClass)) rule.source_class = sourceClass;
        if (targetClass !== null && !isNaN(targetClass)) rule.target_class = targetClass;

        interaction.rules.push(rule);
    }

    for (const death of deaths) {
        let checkStats = getConnectedNodesFromInput(death, 'check_stat');
        if (checkStats.length === 0) checkStats = getConnectedNodesFromInput(death, 'input_1');

        let statIndex = 0;
        if (checkStats.length > 0) {
            statIndex = parseInt(checkStats[0].data.statIndex, 10);
        }

        removal.rules.push({
            stat_index: statIndex,
            threshold: parseFloat(death.data.threshold) || 0,
            condition: death.data.condition || 'LessThanEqual'
        });
    }

    for (const nav of navigations) {
        let followers = getConnectedNodesFromInput(nav, 'follower');
        if (followers.length === 0) followers = getConnectedNodesFromInput(nav, 'input_1');

        let targetFactions = getConnectedNodesFromInput(nav, 'target_faction');
        if (targetFactions.length === 0) targetFactions = getConnectedNodesFromInput(nav, 'input_2');

        let targetWaypoints = getConnectedNodesFromInput(nav, 'waypoint');
        if (targetWaypoints.length === 0) targetWaypoints = getConnectedNodesFromInput(nav, 'input_3');

        if (followers.length === 0) continue;

        const followerId = parseInt(followers[0].data.factionId, 10);
        if (factionsWithGeneral.has(followerId)) continue; // skip

        let targetObj = null;
        if (targetFactions.length > 0) {
            targetObj = { type: 'Faction', faction_id: parseInt(targetFactions[0].data.factionId, 10) };
        } else if (targetWaypoints.length > 0) {
            targetObj = { type: 'Waypoint', x: parseFloat(targetWaypoints[0].data.x), y: parseFloat(targetWaypoints[0].data.y) };
        }

        if (targetObj) {
            navigation.rules.push({
                follower_faction: followerId,
                target: targetObj
            });
        }
    }

    for (const rel of relationships) {
        let factionsA = getConnectedNodesFromInput(rel, 'faction_a');
        if (factionsA.length === 0) factionsA = getConnectedNodesFromInput(rel, 'input_1');

        let factionsB = getConnectedNodesFromInput(rel, 'faction_b');
        if (factionsB.length === 0) factionsB = getConnectedNodesFromInput(rel, 'input_2');

        if (factionsA.length > 0 && factionsB.length > 0) {
            const fidA = parseInt(factionsA[0].data.factionId, 10);
            const fidB = parseInt(factionsB[0].data.factionId, 10);
            const type = rel.data.relationType;

            if (type === 'hostile') {
                aggro.push({ source: fidA, target: fidB, allow_combat: true });
                aggro.push({ source: fidB, target: fidA, allow_combat: true });
            } else if (type === 'allied' || type === 'neutral') {
                aggro.push({ source: fidA, target: fidB, allow_combat: false });
                aggro.push({ source: fidB, target: fidA, allow_combat: false });
            }
        }
    }

    return { spawns, navigation, interaction, removal, aggro, brains, errors };
}

/**
 * Execute a compiled scenario by sending WS commands.
 * @param {object} scenario
 * @param {Function} sendCommand - (cmd: string, params: object) => boolean
 */
export function executeScenario(scenario, sendCommand) {
    if (scenario.errors && scenario.errors.length > 0) {
        return { success: false, errors: scenario.errors };
    }

    // Stop previous brain runners
    for (const runner of activeBrainRunners) {
        if (runner && typeof runner.stop === 'function') runner.stop();
    }
    activeBrainRunners = [];

    const factionIds = new Set(scenario.spawns.map(s => s.faction_id));
    for (const fid of factionIds) {
        sendCommand('kill_all', { faction_id: fid });
    }

    if (scenario.navigation && scenario.navigation.rules && scenario.navigation.rules.length > 0) {
        sendCommand('set_navigation', scenario.navigation);
    }

    if (scenario.interaction && scenario.interaction.rules && scenario.interaction.rules.length > 0) {
        sendCommand('set_interaction', scenario.interaction);
    }

    if (scenario.removal && scenario.removal.rules && scenario.removal.rules.length > 0) {
        sendCommand('set_removal', scenario.removal);
    }

    if (scenario.aggro && scenario.aggro.length > 0) {
        for (const agg of scenario.aggro) {
            sendCommand('set_aggro_mask', agg);
        }
    }

    setTimeout(() => {
        if (scenario.spawns) {
            for (const spawn of scenario.spawns) {
                sendCommand('spawn_wave', spawn);
            }
        }

        setTimeout(() => {
            // Phase 5: Brain Init
            if (scenario.brains && scenario.brains.length > 0) {
                for (const brain of scenario.brains) {
                    const runner = startBrainRunner(brain, sendCommand);
                    activeBrainRunners.push(runner);
                }
            }

            sendCommand('toggle_sim', {});
        }, 200);

    }, 100);

    return { success: true, errors: [] };
}

/**
 * Convert existing preset JSON to Drawflow graph JSON.
 * Uses Drawflow's numbered port convention: output_1, input_1, etc.
 * @param {string} presetKey
 * @returns {object} - Drawflow-compatible export JSON
 */
export function presetToGraph(presetKey) {
    const preset = getPreset(presetKey);
    if (!preset) return { drawflow: { Home: { data: {} } } };

    const nodesData = {};
    let nextNodeId = 1;

    /**
     * Add a node in Drawflow's internal JSON format.
     * @param {string} name - Node type name
     * @param {number} numInputs - Number of input ports
     * @param {number} numOutputs - Number of output ports
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {object} dataObj - Node data
     * @returns {number} - Node ID
     */
    const addNode = (name, numInputs, numOutputs, x, y, dataObj) => {
        const id = nextNodeId++;
        const inputs = {};
        for (let i = 1; i <= numInputs; i++) {
            inputs[`input_${i}`] = { connections: [] };
        }
        const outputs = {};
        for (let i = 1; i <= numOutputs; i++) {
            outputs[`output_${i}`] = { connections: [] };
        }

        nodesData[id] = {
            id,
            name,
            data: Object.assign({}, dataObj),
            class: name,
            html: getNodeHTML(name),
            typenode: false,
            inputs,
            outputs,
            pos_x: x,
            pos_y: y,
        };
        return id;
    };

    /**
     * Connect two nodes using Drawflow's numbered port format.
     * @param {number} fromId - Source node ID
     * @param {number} fromPort - Source output port number (1-based)
     * @param {number} toId - Target node ID
     * @param {number} toPort - Target input port number (1-based)
     */
    const connectNodes = (fromId, fromPort, toId, toPort) => {
        const outKey = `output_${fromPort}`;
        const inKey = `input_${toPort}`;
        if (!nodesData[fromId] || !nodesData[toId]) return;
        if (!nodesData[fromId].outputs[outKey] || !nodesData[toId].inputs[inKey]) {
            console.warn(`[Graph] Skipping connection: ${fromId}.${outKey} → ${toId}.${inKey} (port not found)`);
            return;
        }
        nodesData[fromId].outputs[outKey].connections.push({ node: String(toId), output: inKey });
        nodesData[toId].inputs[inKey].connections.push({ node: String(fromId), input: outKey });
    };

    const factionNodes = {};
    const unitNodes = {};
    const statsNodes = {};

    const factionXStart = 100;
    const factionYLoc = 80;
    const xSpacing = 500;

    // ── Create Faction + Unit + Stat nodes per spawn ──
    for (let i = 0; i < preset.spawns.length; i++) {
        const spawn = preset.spawns[i];
        const fId = spawn.faction_id;
        const rootX = factionXStart + (i * xSpacing);

        // Faction node: 0 inputs, 4 outputs (units, relationship, trait, general)
        const factionNodeId = addNode('faction', 0, 4, rootX, factionYLoc, {
            factionId: fId,
            name: `Faction ${fId}`,
            color: fId === 0 ? '#ef476f' : (fId === 1 ? '#06d6a0' : '#118ab2'),
            spawnCount: spawn.amount,
            spawnX: spawn.x,
            spawnY: spawn.y,
            spawnSpread: spawn.spread
        });
        factionNodes[fId] = factionNodeId;

        // Unit node: 4 inputs (from_faction, stats, combat, death), 2 outputs (attacker, target)
        const unitNodeId = addNode('unit', 4, 2, rootX + 50, factionYLoc + 220, {
            unitName: `Unit ${fId}`,
            classId: fId
        });
        unitNodes[fId] = unitNodeId;

        // Connect: Faction.output_1 (units) → Unit.input_1 (from_faction)
        connectNodes(factionNodeId, 1, unitNodeId, 1);

        // Stat nodes
        if (spawn.stats) {
            for (let j = 0; j < spawn.stats.length; j++) {
                const stat = spawn.stats[j];
                // Stat node: 0 inputs, 1 output (value)
                const statNodeId = addNode('stat', 0, 1, rootX - 180, factionYLoc + 400 + (j * 170), {
                    label: stat.index === 0 ? 'HP' : `Stat ${stat.index}`,
                    statIndex: stat.index,
                    initialValue: stat.value
                });
                statsNodes[`${fId}_${stat.index}`] = statNodeId;
                // Connect: Stat.output_1 (value) → Unit.input_2 (stats)
                connectNodes(statNodeId, 1, unitNodeId, 2);
            }
        }
    }

    // ── Death nodes ──
    for (const rule of preset.removal || []) {
        for (const fId of Object.keys(unitNodes)) {
            const statKey = `${fId}_${rule.stat_index}`;
            const statNodeId = statsNodes[statKey];
            if (statNodeId) {
                const rootX = nodesData[statNodeId].pos_x + 350;
                const rootY = nodesData[statNodeId].pos_y;
                // Death node: 1 input (check_stat), 0 outputs
                const deathNodeId = addNode('death', 1, 0, rootX, rootY, {
                    condition: rule.condition,
                    threshold: rule.threshold
                });
                // Connect: Stat.output_1 (value) → Death.input_1 (check_stat)
                connectNodes(statNodeId, 1, deathNodeId, 1);
            }
        }
    }

    // ── Combat nodes ──
    let combatY = factionYLoc + 450;
    for (const rule of preset.interaction || []) {
        let rootX = 300;
        if (factionNodes[rule.source_faction] && factionNodes[rule.target_faction]) {
            rootX = (nodesData[factionNodes[rule.source_faction]].pos_x +
                     nodesData[factionNodes[rule.target_faction]].pos_x) / 2;
        }
        const e = rule.effects[0] || { stat_index: 0, delta_per_second: 0 };
        // Combat node: 3 inputs (attacker, target, damage_stat), 0 outputs
        const combatNodeId = addNode('combat', 3, 0, rootX, combatY, {
            attackType: 'melee',
            damage: e.delta_per_second,
            range: rule.range,
            cooldownTicks: rule.cooldown_ticks || 0
        });
        combatY += 220;

        const sourceUnitId = unitNodes[rule.source_faction];
        const targetUnitId = unitNodes[rule.target_faction];
        // Connect: Unit.output_1 (attacker) → Combat.input_1 (attacker)
        if (sourceUnitId) connectNodes(sourceUnitId, 1, combatNodeId, 1);
        // Connect: Unit.output_2 (target) → Combat.input_2 (target)
        if (targetUnitId) connectNodes(targetUnitId, 2, combatNodeId, 2);

        // Connect damage stat to combat
        const dmgStatKey = `${rule.target_faction}_${e.stat_index}`;
        if (statsNodes[dmgStatKey]) {
            connectNodes(statsNodes[dmgStatKey], 1, combatNodeId, 3);
        }
    }

    // ── Navigation nodes ──
    let navY = factionYLoc - 100;
    for (const rule of preset.navigation || []) {
        const fId = rule.follower_faction;
        const fromFactionId = factionNodes[fId];
        if (!fromFactionId) continue;

        const rootX = nodesData[fromFactionId].pos_x + 200;
        // Navigation node: 3 inputs (follower, target_faction, waypoint), 0 outputs
        const navNodeId = addNode('navigation', 3, 0, rootX, navY, {});

        // Connect: Faction.output_4 (general) → Nav.input_1 (follower)
        connectNodes(fromFactionId, 4, navNodeId, 1);

        if (rule.target.type === 'Faction') {
            const targetFactionId = factionNodes[rule.target.faction_id];
            if (targetFactionId) {
                // Connect: TargetFaction.output_4 (general) → Nav.input_2 (target_faction)
                connectNodes(targetFactionId, 4, navNodeId, 2);
            }
        } else if (rule.target.type === 'Waypoint') {
            // Waypoint node: 0 inputs, 1 output (position)
            const waypointId = addNode('waypoint', 0, 1, rootX + 250, navY, {
                x: rule.target.x,
                y: rule.target.y
            });
            // Connect: Waypoint.output_1 (position) → Nav.input_3 (waypoint)
            connectNodes(waypointId, 1, navNodeId, 3);
        }
        navY -= 170;
    }

    return { drawflow: { Home: { data: nodesData } } };
}

