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

    for (const evt of ["execution_start", "execution_cached", "execution_error"]) {
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

    for (const evt of ["execution_start", "execution_cached", "execution_error"]) {
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
        }
    },

    setup(app) {
        setupAnySelectionEvents();
        setupForkSelectionEvents();
    },
});
