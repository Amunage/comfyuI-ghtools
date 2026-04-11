import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// ─── 공통 유틸 ──────────────────────────────────────────

async function sendMessage(endpoint, nodeId, action) {
    try {
        const response = await api.fetchApi(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ node_id: nodeId, action }),
        });
        return await response.json();
    } catch (error) {
        console.error(`Message to ${endpoint} failed:`, error);
        return { code: -1, error: error.message };
    }
}

function disableSerialize(widget) {
    if (!widget.options) widget.options = {};
    widget.options.serialize = false;
}

function addActionButton(node, name, activeName, action, sendFn) {
    const btn = node.addWidget("button", name, null, function () {
        if (node.isWaiting) {
            sendFn(node.id, action);
            node.isWaiting = false;
            node.updateButtons();
        }
    });
    disableSerialize(btn);
    btn._label = name;
    btn._activeLabel = activeName;
    return btn;
}

function resetNodesOnEvent(eventName, nodeType) {
    api.addEventListener(eventName, () => {
        app.graph._nodes.forEach((node) => {
            if (node.type === nodeType) {
                node.isWaiting = false;
                if (node.updateButtons) node.updateButtons();
            }
        });
    });
}

function setupSelectionBoolean(nodeType) {
    const config = {
        inputPrefix: "input",
        togglePrefix: "select",
        inputType: "*",
    };

    const refreshNode = (node, options = {}) => {
        const { syncInputs = false, deferred = false } = options;
        const run = () => {
            ensureSelectionBooleanInput(node, config);
            if (syncInputs) {
                syncSelectionBooleanInputs(node, config);
            }
            syncSelectionBooleanWidgets(node, config);
            updateSelectionBooleanInputLabels(node, config.inputPrefix);
            updateSelectionBooleanToggleLabels(node, config);
            node.setDirtyCanvas(true, true);
        };

        if (deferred) {
            setTimeout(run, 0);
            return;
        }

        run();
    };

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const result = onNodeCreated?.apply(this, arguments);

        refreshNode(this);
        return result;
    };

    const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function () {
        const result = onConnectionsChange?.apply(this, arguments);
        refreshNode(this, { syncInputs: true });
        return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
        const result = onConfigure?.apply(this, arguments);
        refreshNode(this, { syncInputs: true, deferred: true });
        return result;
    };

    const onAdded = nodeType.prototype.onAdded;
    nodeType.prototype.onAdded = function () {
        const result = onAdded?.apply(this, arguments);
        refreshNode(this, { syncInputs: true, deferred: true });
        return result;
    };
}

function ensureSelectionBooleanInput(node, config) {
    const hasInput = node.inputs?.some((input) => input.name?.startsWith(config.inputPrefix));
    if (!hasInput) {
        node.addInput(`${config.inputPrefix}1`, config.inputType);
    }
}

function syncSelectionBooleanInputs(node, config) {
    if (!node?.inputs) {
        return;
    }

    const collectInputs = () =>
        node.inputs.filter((input) => input.name?.startsWith(config.inputPrefix));

    let inputs = collectInputs();
    if (!inputs.length) {
        node.addInput(`${config.inputPrefix}1`, config.inputType);
        inputs = collectInputs();
    }

    const trailingUnlinked = [];
    for (let index = inputs.length - 1; index >= 0; index--) {
        const input = inputs[index];
        if (input.link) {
            break;
        }
        trailingUnlinked.push(input);
    }

    while (trailingUnlinked.length > 1) {
        const removableInput = trailingUnlinked.pop();
        const inputIndex = node.inputs.indexOf(removableInput);
        if (inputIndex >= 0) {
            node.removeInput(inputIndex);
        }
    }

    inputs = collectInputs();
    const lastInput = inputs[inputs.length - 1];
    if (!lastInput || lastInput.link) {
        node.addInput(`${config.inputPrefix}${inputs.length + 1}`, config.inputType);
        inputs = collectInputs();
    }

    let validIndex = 1;
    node.inputs.forEach((input) => {
        if (input.name?.startsWith(config.inputPrefix)) {
            input.name = `${config.inputPrefix}${validIndex}`;
            input.label = input.name;
            validIndex += 1;
        }
    });
}

function syncSelectionBooleanWidgets(node, config) {
    if (!node.widgets) {
        node.widgets = [];
    }

    const desiredCount = countSelectionBooleanInputs(node, config.inputPrefix);
    const toggles = node.widgets.filter((widget) => widget.__ghSelectionBooleanToggle === true);

    while (toggles.length < desiredCount) {
        const nextIndex = toggles.length + 1;
        const widget = node.addWidget("toggle", `${config.togglePrefix}_${nextIndex}`, false, undefined, {
            on: "ON",
            off: "OFF",
        });
        widget.__ghSelectionBooleanToggle = true;
        toggles.push(widget);
    }

    for (let index = toggles.length - 1; index >= desiredCount; index--) {
        const widget = toggles[index];
        const widgetIndex = node.widgets.indexOf(widget);
        if (widgetIndex >= 0) {
            node.widgets.splice(widgetIndex, 1);
        }
        toggles.splice(index, 1);
    }

    toggles.forEach((widget, index) => {
        const inputIndex = index + 1;
        widget.name = `${config.togglePrefix}_${inputIndex}`;
        widget.options = { on: "ON", off: "OFF" };
        widget.callback = (value) => {
            applyExclusiveSelectionBooleanToggle(node, config, value ? inputIndex : null);
            updateSelectionBooleanToggleLabels(node, config);
        };
    });

    applyExclusiveSelectionBooleanToggle(node, config);
    updateSelectionBooleanToggleLabels(node, config);
}

function countSelectionBooleanInputs(node, prefix) {
    if (!node?.inputs) {
        return 0;
    }
    return node.inputs.filter((input) => input.name?.startsWith(prefix)).length;
}

function updateSelectionBooleanInputLabels(node, prefix) {
    if (!node?.inputs) {
        return;
    }

    node.inputs.forEach((input) => {
        if (!input.name?.startsWith(prefix)) {
            return;
        }

        const suffix = input.name.slice(prefix.length);
        const inputIndex = Number.parseInt(suffix, 10);
        if (Number.isNaN(inputIndex)) {
            input.label = input.name;
            return;
        }

        input.label = getSelectionBooleanConnectedLabel(node, prefix, inputIndex) || input.name;
    });
}

function updateSelectionBooleanToggleLabels(node, config) {
    const toggles = node.widgets?.filter((widget) => widget.__ghSelectionBooleanToggle === true) ?? [];
    toggles.forEach((widget, index) => {
        const inputIndex = index + 1;
        widget.name = `${config.togglePrefix}_${inputIndex}`;
        widget.label = getSelectionBooleanConnectedLabel(node, config.inputPrefix, inputIndex) || "(none)";
    });
}

function applyExclusiveSelectionBooleanToggle(node, config, preferredIndex = null) {
    const toggles = node.widgets?.filter((widget) => widget.__ghSelectionBooleanToggle === true) ?? [];
    if (!toggles.length) {
        return;
    }

    const connectedIndices = [];
    toggles.forEach((widget, index) => {
        const inputIndex = index + 1;
        if (isSelectionBooleanInputConnected(node, config.inputPrefix, inputIndex)) {
            connectedIndices.push(inputIndex);
        } else {
            widget.value = false;
        }
    });

    if (!connectedIndices.length) {
        node.setDirtyCanvas(true, true);
        return;
    }

    let selectedIndex = preferredIndex;
    if (!selectedIndex || !connectedIndices.includes(selectedIndex)) {
        const enabledConnected = connectedIndices.filter((index) => Boolean(toggles[index - 1]?.value));
        selectedIndex = enabledConnected[0] ?? connectedIndices[0];
    }

    connectedIndices.forEach((index) => {
        toggles[index - 1].value = index === selectedIndex;
    });

    node.setDirtyCanvas(true, true);
}

function isSelectionBooleanInputConnected(node, prefix, index) {
    if (!node?.inputs) {
        return false;
    }

    const input = node.inputs.find((candidate) => candidate.name === `${prefix}${index}`);
    return Boolean(input?.link);
}

function getSelectionBooleanConnectedLabel(node, prefix, index) {
    if (!node?.inputs) {
        return null;
    }

    const input = node.inputs.find((candidate) => candidate.name === `${prefix}${index}`);
    if (!input?.link) {
        return null;
    }

    const graph = node.graph ?? app.graph;
    const link = graph?.links?.[input.link];
    if (!link) {
        return null;
    }

    const originNode = graph?.getNodeById?.(link.origin_id);
    return originNode?.title ?? null;
}

// ─── GH Selection Input (GHAnySelection) ───────────────

function setupAnySelection(nodeType) {
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const result = onNodeCreated?.apply(this, arguments);

        this.isWaiting = false;
        const send = (id, action) => sendMessage("/ghtools/any_selection_message", id, action);

        this.buttonA = addActionButton(this, "Select A", "▶ Select A", "A", send);
        this.buttonB = addActionButton(this, "Select B", "▶ Select B", "B", send);
        this.retryButton = addActionButton(this, "Retry", "↻ Retry", "retry", send);
        this.cancelButton = addActionButton(this, "Cancel", "✖ Cancel", "cancel", send);

        this.updateButtons = function () {
            const waiting = this.isWaiting;
            for (const btn of [this.buttonA, this.buttonB, this.retryButton, this.cancelButton]) {
                btn.name = waiting ? btn._activeLabel : btn._label;
            }
            this.bgcolor = waiting ? "#335533" : null;
            this.setDirtyCanvas(true, true);
        };

        this.updateButtons();
        return result;
    };
}

function setupAnySelectionEvents() {
    const TYPE = "GHAnySelection";

    api.addEventListener("ghtools-any-waiting", (event) => {
        const node = app.graph._nodes_by_id[event.detail.id];
        if (node && node.type === TYPE) {
            node.isWaiting = true;
            node.updateButtons();
        }
    });

    api.addEventListener("ghtools-any-keep-selection", (event) => {
        const node = app.graph._nodes_by_id[event.detail.id];
        if (node && node.type === TYPE) {
            node.isWaiting = false;
            node.updateButtons();
        }
    });

    api.addEventListener("ghtools-any-retry", (event) => {
        console.log("[AnySelection] Retry requested, re-queueing prompt...");
        setTimeout(() => { app.queuePrompt(0, 1); }, 100);
    });

    for (const evt of ["execution_start", "execution_cached", "execution_error", "execution_interrupted"]) {
        resetNodesOnEvent(evt, TYPE);
    }
}

// ─── GH Selection Output (GHForkSelection) ─────────────

function setupForkSelection(nodeType) {
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const result = onNodeCreated?.apply(this, arguments);

        this.isWaiting = false;
        const send = (id, action) => sendMessage("/ghtools/fork_selection_message", id, action);

        this.buttonA = addActionButton(this, "Send to A", "▶ Send to A", "A", send);
        this.buttonB = addActionButton(this, "Send to B", "▶ Send to B", "B", send);
        this.retryButton = addActionButton(this, "Retry", "↻ Retry", "retry", send);
        this.cancelButton = addActionButton(this, "Cancel", "✖ Cancel", "cancel", send);

        this.updateButtons = function () {
            const waiting = this.isWaiting;
            for (const btn of [this.buttonA, this.buttonB, this.retryButton, this.cancelButton]) {
                btn.name = waiting ? btn._activeLabel : btn._label;
            }
            this.bgcolor = waiting ? "#335533" : null;
            this.setDirtyCanvas(true, true);
        };

        this.updateButtons();
        return result;
    };
}

function setupForkSelectionEvents() {
    const TYPE = "GHForkSelection";

    api.addEventListener("ghtools-fork-waiting", (event) => {
        const node = app.graph._nodes_by_id[event.detail.id];
        if (node && node.type === TYPE) {
            node.isWaiting = true;
            node.updateButtons();
        }
    });

    api.addEventListener("ghtools-fork-keep-selection", (event) => {
        const node = app.graph._nodes_by_id[event.detail.id];
        if (node && node.type === TYPE) {
            node.isWaiting = false;
            node.updateButtons();
        }
    });

    api.addEventListener("ghtools-fork-retry", (event) => {
        console.log("[ForkSelection] Retry requested, re-queueing prompt...");
        setTimeout(() => { app.queuePrompt(0, 1); }, 100);
    });

    for (const evt of ["execution_start", "execution_cached", "execution_error", "execution_interrupted"]) {
        resetNodesOnEvent(evt, TYPE);
    }
}

// ─── 등록 ───────────────────────────────────────────────

app.registerExtension({
    name: "ghtools.selectionNode",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GHAnySelection") {
            setupAnySelection(nodeType);
        } else if (nodeData.name === "GHForkSelection") {
            setupForkSelection(nodeType);
        } else if (nodeData.name === "GHSelectionBoolean") {
            setupSelectionBoolean(nodeType);
        }
    },

    setup(app) {
        setupAnySelectionEvents();
        setupForkSelectionEvents();
    },
});
