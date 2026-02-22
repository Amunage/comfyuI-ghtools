import { app } from "../../scripts/app.js";

const SUPPORTED_NODES = {
    GHtextConcatenate: { inputPrefix: "text", togglePrefix: null },
    GHtextConcatenateToggle: { inputPrefix: "text", togglePrefix: "toggle" },
};

app.registerExtension({
    name: "GHTools.TextConcatenate",

    beforeRegisterNodeDef(nodeType, nodeData) {
        const config = SUPPORTED_NODES[nodeData?.name];
        if (!config) {
            return;
        }

        const inputName = config.inputPrefix;
        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalOnNodeCreated?.apply(this, arguments);
            const hasTextInput = this.inputs?.some((input) => input.name.startsWith(inputName));
            if (!hasTextInput) {
                this.addInput(`${inputName}1`, "STRING");
            }
            syncToggleWidgets(
                this,
                config.togglePrefix,
                countTextInputs(this, inputName),
                inputName
            );
            updateInputLabels(this, inputName);
            return result;
        };

        const originalOnConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (type, index, connected, linkInfo) {
            const result = originalOnConnectionsChange?.apply(this, arguments);
            if (!linkInfo) {
                return result;
            }

            dynamicConnection(
                this,
                index,
                connected,
                inputName,
                this.inputs?.[0]?.type ?? "STRING"
            );
            syncToggleWidgets(
                this,
                config.togglePrefix,
                countTextInputs(this, inputName),
                inputName
            );
            updateInputLabels(this, inputName);
            return result;
        };
    },
});

function dynamicConnection(
    node,
    index,
    connected,
    connectionPrefix = "input_",
    connectionType = "STRING"
) {
    if (!node?.inputs) {
        return;
    }

    const ensureInputsList = () =>
        node.inputs
            .map((input, idx) => ({ input, idx }))
            .filter(({ input }) => input.name?.startsWith(connectionPrefix));

    let prefixedInputs = ensureInputsList();
    if (!prefixedInputs.length) {
        node.addInput(`${connectionPrefix}1`, connectionType);
        prefixedInputs = ensureInputsList();
    }

    const trailingUnlinked = [];
    for (let i = prefixedInputs.length - 1; i >= 0; i--) {
        const { input } = prefixedInputs[i];
        if (input.link) {
            break;
        }
        trailingUnlinked.push(input);
    }

    while (trailingUnlinked.length > 1) {
        const inputToRemove = trailingUnlinked.pop();
        const idx = node.inputs.indexOf(inputToRemove);
        if (idx >= 0) {
            node.removeInput(idx);
        }
    }

    prefixedInputs = ensureInputsList();
    const lastInput = prefixedInputs[prefixedInputs.length - 1]?.input;
    if (!lastInput || lastInput.link) {
        node.addInput(`${connectionPrefix}${prefixedInputs.length + 1}`, connectionType);
        prefixedInputs = ensureInputsList();
    }

    let validIndex = 1;
    node.inputs.forEach((input) => {
        if (input.name.startsWith(connectionPrefix)) {
            input.name = `${connectionPrefix}${validIndex++}`;
            input.label = input.name;
        }
    });
}

function syncToggleWidgets(node, togglePrefix, desiredCount, inputPrefix) {
    if (!togglePrefix || desiredCount <= 0) {
        return;
    }
    if (!node.widgets) {
        node.widgets = [];
    }

    const toggles = node.widgets.filter((w) => w.__ghToggle === true);

    while (toggles.length < desiredCount) {
        const idx = toggles.length + 1;
        const widget = node.addWidget("toggle", `${togglePrefix}_${idx}`, true, undefined, {
            on: "ON",
            off: "OFF",
        });
        widget.__ghToggle = true;
        toggles.push(widget);
    }

    toggles.forEach((widget, idx) => {
        if (idx < desiredCount) {
            widget.name = `${togglePrefix}_${idx + 1}`;
            widget.options = { on: "ON", off: "OFF" };
        }
    });

    for (let i = toggles.length - 1; i >= desiredCount; i--) {
        const widget = toggles[i];
        const index = node.widgets.indexOf(widget);
        if (index >= 0) {
            node.widgets.splice(index, 1);
        }
    }

    updateToggleLabels(node, togglePrefix, inputPrefix);
}

function countTextInputs(node, prefix) {
    if (!node.inputs) {
        return 0;
    }
    return node.inputs.filter((input) => input.name?.startsWith(prefix)).length;
}

function updateInputLabels(node, prefix) {
    if (!node?.inputs) {
        return;
    }
    node.inputs.forEach((input) => {
        if (!input.name?.startsWith(prefix)) {
            return;
        }
        const idx = parseInt(input.name.slice(prefix.length), 10);
        if (Number.isNaN(idx)) {
            input.label = input.name;
            return;
        }
        const label = getConnectedInputLabel(node, prefix, idx);
        input.label = label || input.name;
    });
}

function updateToggleLabels(node, togglePrefix, inputPrefix) {
    if (!togglePrefix || !node.widgets) {
        return;
    }
    const toggles = node.widgets.filter((w) => w.__ghToggle === true);
    toggles.forEach((widget, idx) => {
        const inputLabel = getConnectedInputLabel(node, inputPrefix, idx + 1);
        const baseName = `${togglePrefix}_${idx + 1}`;
        widget.name = baseName;
        if (inputLabel) {
            widget.label = inputLabel;
        } else {
            widget.label = "(none)";
        }
    });
}

function getConnectedInputLabel(node, prefix, index) {
    if (!node?.inputs) {
        return null;
    }
    const targetName = `${prefix}${index}`;
    const input = node.inputs.find((inp) => inp.name === targetName);
    if (!input || !input.link) {
        return null;
    }
    const link = app.graph.links?.[input.link];
    if (!link) {
        return null;
    }
    const originNode = app.graph.getNodeById(link.origin_id);
    if (!originNode) {
        return null;
    }
    return originNode.title;
}
