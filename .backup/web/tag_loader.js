import { app } from "../../scripts/app.js";

const TAG_DROPDOWN_MAX_HEIGHT = "480px";
const tagMenuState = {
    lastPointerX: 0,
    lastPointerY: 0,
    lastPointerTime: 0,
};
const tagHelpDOM = createTagHelpDOM();
ensureTagDropdownStyle();
observeTagDropdownMenus();
trackLastPointerPosition();

function ensureTagDropdownStyle() {
    if (document.getElementById("ghtools-tag-loader-style")) return;
    const style = document.createElement("style");
    style.id = "ghtools-tag-loader-style";
    style.textContent = `
        .litecontextmenu {
            max-height: ${TAG_DROPDOWN_MAX_HEIGHT};
            overflow-y: auto;
        }
    `;
    document.head.appendChild(style);
}

function applyTagDropdownHeight(menu) {
    if (!(menu instanceof HTMLElement)) return;
    if (!menu.classList.contains("litecontextmenu")) return;
    menu.style.setProperty("max-height", TAG_DROPDOWN_MAX_HEIGHT, "important");
    menu.style.setProperty("overflow-y", "auto", "important");
    requestAnimationFrame(() => positionTagDropdownMenu(menu));
}

function observeTagDropdownMenus() {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                applyTagDropdownHeight(node);
                if (node instanceof HTMLElement) {
                    node.querySelectorAll?.(".litecontextmenu").forEach(applyTagDropdownHeight);
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

function trackLastPointerPosition() {
    document.addEventListener(
        "pointerdown",
        (event) => {
            tagMenuState.lastPointerX = event.clientX;
            tagMenuState.lastPointerY = event.clientY;
            tagMenuState.lastPointerTime = Date.now();
        },
        true
    );
}

function positionTagDropdownMenu(menu) {
    if (!(menu instanceof HTMLElement) || !menu.isConnected) return;
    if (Date.now() - tagMenuState.lastPointerTime > 1000) return;

    const rect = menu.getBoundingClientRect();
    const margin = 8;
    const left = Math.max(
        margin,
        Math.min(tagMenuState.lastPointerX + 8, window.innerWidth - rect.width - margin)
    );
    const top = Math.max(
        margin,
        Math.min(tagMenuState.lastPointerY + 8, window.innerHeight - rect.height - margin)
    );

    menu.style.setProperty("left", `${left}px`, "important");
    menu.style.setProperty("top", `${top}px`, "important");
}

function createTagHelpDOM() {
    const panel = document.createElement("div");
    panel.style.position = "fixed";
    panel.style.top = "16px";
    panel.style.right = "16px";
    panel.style.width = "420px";
    panel.style.maxHeight = "80vh";
    panel.style.padding = "16px";
    panel.style.overflowY = "auto";
    panel.style.background = "#1f1f1f";
    panel.style.color = "#f5f5f5";
    panel.style.border = "1px solid #444";
    panel.style.borderRadius = "8px";
    panel.style.boxShadow = "0 8px 24px rgba(0, 0, 0, 0.35)";
    panel.style.zIndex = "10000";
    panel.style.display = "none";
    document.body.appendChild(panel);
    return panel;
}

function chainCallback(target, callbackName, fn) {
    const original = target[callbackName];
    target[callbackName] = function () {
        const result = original?.apply(this, arguments);
        const chained = fn.apply(this, arguments);
        return chained ?? result;
    };
}

function setTagHelpContent(title, description) {
    const safeDescription = String(description || "").replace(/\n/g, "<br>");
    tagHelpDOM.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <strong style="font-size:18px;">${title}</strong>
        <button type="button" style="background:none;border:none;color:#f5f5f5;font-size:18px;cursor:pointer;">x</button>
    </div>
    <div style="line-height:1.5;">${safeDescription}</div>`;
    tagHelpDOM.querySelector("button")?.addEventListener("click", () => {
        tagHelpDOM.style.display = "none";
    });
}

function addHelpBadge(node, description) {
    if (!description) return;
    const originalComputeSize = node.computeSize;
    node.computeSize = function () {
        const size = originalComputeSize.apply(this, arguments);
        if (!this.title) return size;
        size[0] = Math.max(size[0], app.canvas.title_text_font ? size[0] + 24 : size[0]);
        return size;
    };

    node._tagDescription = description;
    chainCallback(node, "onDrawForeground", function (ctx) {
        if (this?.flags?.collapsed) return;
        ctx.save();
        ctx.font = "bold 20px Arial";
        ctx.fillStyle = "#f5f5f5";
        ctx.fillText("?", this.size[0] - 18, -8);
        ctx.restore();
    });
    chainCallback(node, "onMouseDown", function (e, pos) {
        if (this?.flags?.collapsed) return;
        if (pos[1] < 0 && pos[0] + LiteGraph.NODE_TITLE_HEIGHT > this.size[0]) {
            if (tagHelpDOM.style.display === "block" && tagHelpDOM.dataset.nodeId === String(this.id)) {
                tagHelpDOM.style.display = "none";
                return true;
            }
            tagHelpDOM.dataset.nodeId = String(this.id);
            setTagHelpContent(this.title || "Node Help", this._tagDescription);
            tagHelpDOM.style.display = "block";
            return true;
        }
    });
}


function getGroupFromNode(nodeData) {
    // TagBodyNode → body, TagFocusNode → focus, etc.
    const name = nodeData?.name || "";
    if (name === "GHTagLoader" || name === "TagLoader" || name === "TagAllNode") {
        return "all";
    }
    const m = name.match(/^Tag([A-Za-z0-9]+)Node$/);
    if (!m) return null;
    return m[1].toLowerCase();
}

function getWidgetBaseGroup(group) {
    return group === "all" ? "tag" : group;
}

function parseSectionNames(value) {
    return Array.from(
        new Set(
            String(value || "")
                .split(",")
                .map((part) => part.trim().toLowerCase())
                .filter(Boolean)
        )
    );
}

function getTagStateFromSections(sectionValues, selectedSections, fallbackGroup) {
    const effectiveSections = selectedSections.length ? selectedSections : Object.keys(sectionValues || {});
    const options = ["none"];
    const valueToParent = {};
    effectiveSections.forEach((section, index) => {
        options.push(`----- ${section} -----`);
        const values = sectionValues?.[section] || [];
        for (const value of values) {
            if (value === "none") continue;
            options.push(value);
            valueToParent[value] = section || fallbackGroup;
        }
    });
    if (options.length === 1) options.push(fallbackGroup);
    return { options, valueToParent };
}

function getOptionsAndMap(nodeData, group) {
    // group: "body", "focus", "age", ...
    const inputs = { ...(nodeData?.input?.required || {}), ...(nodeData?.input?.optional || {}) };
    if (!Object.keys(inputs).length) return { options: ["none"], valueToParent: {} };
    // find all dropdowns (array type, not STRING)
    let allOptions = ["none"];
    let valueToParent = {};
    for (const [key, val] of Object.entries(inputs)) {
        if (Array.isArray(val[0])) {
            const opts = val[0];
            for (const v of opts) {
                if (v !== "none") {
                    allOptions.push(v);
                    // parent group: key before _N or just key
                    let parent = key.replace(/_\d+$/, "");
                    // for age: option_map 활용
                    if (nodeData.input?._option_map && nodeData.input._option_map[v]) {
                        parent = nodeData.input._option_map[v].replace(/^TAG_/, "").toLowerCase();
                    }
                    valueToParent[v] = parent;
                }
            }
        }
    }
    // fallback: if no dropdowns found, use group
    if (allOptions.length === 1) allOptions.push(group);
    return { options: Array.from(new Set(allOptions)), valueToParent };
}

function updateTagStateFromSections(node, group) {
    const sectionsWidget = node.widgets?.find((w) => w.name === "sections");
    const selectedSections = parseSectionNames(sectionsWidget?.value);
    const { options, valueToParent } = getTagStateFromSections(node._tagSectionValues, selectedSections, group);
    node._tagOptions = options;
    node._valueToParent = valueToParent;
    reconcileTagWidgets(node, group);
}

function getWidgetByName(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

function getSerializableWidgets(node) {
    return (node.widgets || []).filter((w) => !(w.options && w.options.serialize === false) && w.name !== "Reset");
}

function getSerializableWidgetValuesByName(node) {
    const byName = {};
    for (const widget of getSerializableWidgets(node)) {
        if (widget.name) {
            byName[widget.name] = widget.value;
        }
    }
    return byName;
}

function splitKeywordText(text) {
    return String(text || "")
        .split(/[\n,]+/)
        .map((part) => part.trim())
        .filter(Boolean);
}

function normalizeKeyword(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toLowerCase();
}

function mergeKeywordTexts(prefixTexts, manualText = "") {
    const merged = [];
    const seen = new Set();
    const texts = Array.isArray(prefixTexts) ? prefixTexts : [prefixTexts];

    for (const text of [...texts, manualText]) {
        for (const part of splitKeywordText(text)) {
            const normalized = normalizeKeyword(part);
            if (!normalized || seen.has(normalized)) continue;
            seen.add(normalized);
            merged.push(part);
        }
    }

    return merged.length ? `${merged.join(", ")},` : "";
}

function removeKeywordsFromText(text, keywords) {
    const blocked = new Set(
        splitKeywordText(keywords).map((part) => normalizeKeyword(part)).filter(Boolean)
    );
    if (!blocked.size) return String(text || "").trim();

    const remaining = splitKeywordText(text).filter((part) => !blocked.has(normalizeKeyword(part)));
    return remaining.length ? `${remaining.join(", ")},` : "";
}

function getAutoAppliedText(appliedText, manualText) {
    return removeKeywordsFromText(appliedText, manualText);
}

function hidePreviewWidget(widget) {
    if (!widget) return;
    widget.type = "hidden";
    widget.computeSize = () => [0, -4];
}

function getSelectedPreviewText(node, group) {
    const randomPick = !!getWidgetByName(node, "random_pick")?.value;
    if (randomPick) {
        return "random";
    }

    const activeWidgets = getTagWidgets(node, group)
        .filter((w) => w.value !== "none" && !isTagSeparatorValue(w.value));

    const sectionTags = node._tagSectionTags || {};
    const valueToParent = node._valueToParent || {};
    const previewParts = activeWidgets
        .map((w) => {
            const sectionName = valueToParent[w.value];
            const tag = sectionTags?.[sectionName]?.[w.value] || "";
            const weight = w._tagWeight ?? 1.0;
            return applyWeightToTag(tag, weight);
        })
        .filter(Boolean);

    return mergeKeywordTexts(previewParts);
}

function getManualBaseText(node, textWidget) {
    const currentText = String(textWidget?.value || "").trim();
    const lastAppliedText = String(node._tagLoaderLastAppliedText || "").trim();
    const lastManualText = String(node._tagLoaderLastManualText || "").trim();
    if (currentText === lastAppliedText) {
        return lastManualText;
    }
    if (lastAppliedText) {
        const lastAutoText = getAutoAppliedText(lastAppliedText, lastManualText);
        return removeKeywordsFromText(currentText, lastAutoText);
    }
    const selectedText = getSelectedPreviewText(node, node._tagGroup);
    if (selectedText && selectedText !== "random") {
        return removeKeywordsFromText(currentText, selectedText);
    }
    return currentText;
}

function rememberAppliedText(node, appliedText, manualBaseText) {
    node._tagLoaderLastAppliedText = String(appliedText || "").trim();
    node._tagLoaderLastManualText = String(manualBaseText || "").trim();
}

function syncTextWidget(node, group, previewText = null) {
    const textWidget = getWidgetByName(node, "text");
    if (!textWidget) return "";

    const manualBaseText = getManualBaseText(node, textWidget);
    const selectedText = previewText ?? getSelectedPreviewText(node, group);
    const mergedText = selectedText === "random"
        ? manualBaseText
        : mergeKeywordTexts(selectedText ? [selectedText] : [], manualBaseText);

    textWidget.value = mergedText;
    rememberAppliedText(node, mergedText, manualBaseText);
    app.graph.setDirtyCanvas(true);
    return mergedText;
}

function trimDynamicTagWidgetValues(node, info) {
    if (!Array.isArray(info?.widgets_values) || !Array.isArray(info?._tagWidgets)) return;
    const extraTagCount = Math.max(0, info._tagWidgets.length - 1);
    const activeTagCount = (info._tagWidgets || []).filter(v => v !== "none" && !isTagSeparatorValue(v)).length;
    const extraCount = extraTagCount + activeTagCount;
    if (!extraCount) return;

    const baseName = `${node._tagWidgetBaseGroup || "tag"}_1`;
    const tag1Idx = (node.widgets || []).findIndex((w) => w.name === baseName);
    if (tag1Idx < 0) return;

    const fixed = [...info.widgets_values];
    fixed.splice(tag1Idx + 1, extraCount);
    info.widgets_values = fixed;
}

function restoreWidgetValuesByName(node, info) {
    const byName = info?.ghtools_widget_values_by_name;
    if (!byName || typeof byName !== "object") return;

    for (const widget of getSerializableWidgets(node)) {
        if (!widget.name || !(widget.name in byName)) continue;
        widget.value = byName[widget.name];
    }
}

function ensurePreviewWidget(node) {
    const existingPreview = getWidgetByName(node, "preview");
    if (existingPreview) {
        hidePreviewWidget(existingPreview);
        moveWidgetBefore(node, existingPreview, "text");
        return;
    }
}

function updatePreviewWidget(node, group) {
    const previewWidget = getWidgetByName(node, "preview");
    const previewText = getSelectedPreviewText(node, group);
    if (!previewWidget) return previewText;
    previewWidget.value = previewText;
    app.graph.setDirtyCanvas(true);
    return previewText;
}

app.registerExtension({
    name: "GHTools.TagLoader",
    beforeRegisterNodeDef(nodeType, nodeData) {
        const group = getGroupFromNode(nodeData);
        if (!group) return;
        const helpDescription = nodeData.description;
        nodeData.description = "";
        const { options, valueToParent } = getOptionsAndMap(nodeData, group);
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = origCreated?.apply(this, arguments);
            this.serialize_widgets = true;
            this._tagGroup = group;
            this._tagWidgetBaseGroup = getWidgetBaseGroup(group);
            this._tagSectionValues = nodeData.input?._section_values || null;
            this._tagSectionTags = nodeData.input?._section_tags || null;
            this._tagOptions = options;
            this._valueToParent = valueToParent;
            if (!this.widgets?.find((w) => w.name === "Reset")) {
                const resetBtn = this.addWidget("button", "Reset", "Reset", () => resetTagWidgets(this));
                moveWidgetBefore(this, resetBtn, `${this._tagWidgetBaseGroup}_1`);
            }
            ensurePreviewWidget(this);
            initTagCallbacks(this, group);
            initSectionCallbacks(this, group);
            if (this._tagSectionValues) updateTagStateFromSections(this, group);
            updatePreviewWidget(this, group);
            addHelpBadge(this, helpDescription);
            return result;
        };
        const origSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function (o) {
            const previewText = updatePreviewWidget(this, group);
            syncTextWidget(this, group, previewText);
            if (origSerialize) origSerialize.apply(this, arguments);
            o.widgets_values = getSerializableWidgets(this).map((w) => w.value);
            o.ghtools_widget_values_by_name = getSerializableWidgetValuesByName(this);
            o._tagWidgets = getTagWidgets(this, group).map((w) => w.value);
            o._tagWeights = getTagWidgets(this, group).map((w) => w._tagWeight ?? 1.0);
        };
        const origConfigure = nodeType.prototype.configure;
        nodeType.prototype.configure = function (info) {
            this._tagGroup = group;
            this._tagWidgetBaseGroup = getWidgetBaseGroup(group);
            this._tagSectionValues = nodeData.input?._section_values || null;
            this._tagSectionTags = nodeData.input?._section_tags || null;
            this._tagOptions = options;
            this._valueToParent = valueToParent;
            if (info?._tagWidgets && info._tagWidgets.length > 1) {
                const weights = info._tagWeights || [];
                for (let i = 1; i < info._tagWidgets.length; i++) {
                    const value = info._tagWidgets[i];
                    const parent = group === "all" ? this._tagWidgetBaseGroup : (valueToParent[value] || group);
                    const name = `${parent}_${i + 1}`;
                    if (this.widgets?.find((w) => w.name === name)) continue;
                    const w = this.addWidget(
                        "combo",
                        name,
                        value,
                        () => reconcileTagWidgets(this, group),
                        { values: options, serialize: true }
                    );
                    w.options = { ...(w.options || {}), values: options, serialize: true };
                    w._tagWeight = weights[i] ?? 1.0;
                    moveWidgetBefore(this, w, "text");
                }
            }
            if (info?._tagWidgets?.length > 0 && info._tagWidgets[0] !== "none" && !isTagSeparatorValue(info._tagWidgets[0])) {
                const weights = info._tagWeights || [];
                const tag1Name = `${this._tagWidgetBaseGroup || "tag"}_1`;
                const tag1Widget = getWidgetByName(this, tag1Name);
                if (tag1Widget) tag1Widget._tagWeight = weights[0] ?? 1.0;
            }
            if (!this.widgets?.find((w) => w.name === "Reset")) {
                const resetBtn = this.addWidget("button", "Reset", "Reset", () => resetTagWidgets(this));
                moveWidgetBefore(this, resetBtn, `${this._tagWidgetBaseGroup}_1`);
            }
            ensurePreviewWidget(this);
            trimDynamicTagWidgetValues(this, info);
            if (origConfigure) origConfigure.apply(this, arguments);
            initTagCallbacks(this, group);
            initSectionCallbacks(this, group);
            if (this._tagSectionValues) updateTagStateFromSections(this, group);
            restoreWidgetValuesByName(this, info);
            reconcileTagWidgets(this, group);
            updatePreviewWidget(this, group);
        };
        const origExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (output) {
            if (origExecuted) origExecuted.apply(this, arguments);
            const executedText = Array.isArray(output?.text) ? output.text[0] : "";
            if (!executedText) return;
            const textWidget = getWidgetByName(this, "text");
            if (!textWidget) return;
            const manualBaseText = getManualBaseText(this, textWidget);
            textWidget.value = executedText;
            rememberAppliedText(this, executedText, manualBaseText);
            this.setDirtyCanvas?.(true, true);
        };
    },
});

function moveWidgetBefore(node, widget, beforeName) {
    const idx = node.widgets.indexOf(widget);
    if (idx < 0) return;
    node.widgets.splice(idx, 1);
    const target = node.widgets.findIndex((w) => w.name === beforeName);
    node.widgets.splice(target >= 0 ? target : node.widgets.length, 0, widget);
}

function getTagPrefixes(node, group) {
    const baseGroup = getWidgetBaseGroup(group || node._tagGroup);
    const widgetPrefixes = (node.widgets || [])
        .map((w) => w?.name?.match(/^(.+)_\d+$/)?.[1])
        .filter((name) => name && name !== "sections" && name !== "weight");
    return Array.from(new Set([group, baseGroup, ...Object.values(node._valueToParent || {}), ...widgetPrefixes].filter(Boolean)));
}

function isTagWidget(widget, prefixes) {
    return !!widget?.name && prefixes.some((prefix) => widget.name.startsWith(`${prefix}_`));
}

function isTagSeparatorValue(value) {
    return typeof value === "string" && value.startsWith("-----") && value.endsWith("-----");
}

function isWeightWidget(widget) {
    return !!widget?.name && /^weight_\d+$/.test(widget.name);
}

function getWeightWidgets(node) {
    return (node.widgets || []).filter(isWeightWidget);
}

function applyWeightToTag(tagText, weight) {
    const rounded = Math.round(weight * 100) / 100;
    if (rounded === 1.0) return tagText;
    const wStr = parseFloat(rounded.toFixed(2)).toString();
    const parts = String(tagText || "").split(",").map(s => s.trim()).filter(Boolean);
    if (!parts.length) return tagText;
    return parts.map(p => `(${p}:${wStr})`).join(", ") + ",";
}

const TAG_WEIGHT_AREA_WIDTH = 68;
const TAG_WEIGHT_STEP = 0.05;
const TAG_WEIGHT_MIN = 0.0;
const TAG_WEIGHT_MAX = 3.0;

function drawComboWeightWidget(ctx, node, widget_width, y, H) {
    const w = this;
    const isActive = w.value !== "none" && !isTagSeparatorValue(w.value);
    const margin = 15;
    const WEIGHT_W = isActive ? TAG_WEIGHT_AREA_WIDTH : 0;
    const comboW = widget_width - WEIGHT_W;
    const rr = H * 0.25;

    // Clear default combo rendering
    ctx.fillStyle = node.bgcolor || LiteGraph.NODE_DEFAULT_BGCOLOR || "#353535";
    ctx.fillRect(0, y, widget_width, H);

    // Combo background
    ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR || "#232323";
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(margin, y, comboW - margin * 2, H, rr) : ctx.rect(margin, y, comboW - margin * 2, H);
    ctx.fill();

    // Combo text
    ctx.save();
    ctx.beginPath();
    ctx.rect(margin + 16, y, comboW - margin * 2 - 32, H);
    ctx.clip();
    ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR || "#DDD";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.font = `${Math.round(H * 0.65)}px Arial`;
    ctx.fillText(w.value || "none", margin + 18, y + H * 0.5);
    ctx.restore();

    // Combo arrows
    ctx.fillStyle = LiteGraph.WIDGET_SECONDARY_TEXT_COLOR || "#999";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `${Math.round(H * 0.5)}px Arial`;
    ctx.fillText("\u25C0", margin + 8, y + H * 0.5);
    ctx.fillText("\u25B6", comboW - margin - 8, y + H * 0.5);

    // Weight area
    if (isActive) {
        const weightX = comboW;
        const weightInnerW = WEIGHT_W - margin;
        const weight = w._tagWeight ?? 1.0;

        ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR || "#232323";
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(weightX, y, weightInnerW, H, rr) : ctx.rect(weightX, y, weightInnerW, H);
        ctx.fill();

        ctx.font = `${Math.round(H * 0.5)}px Arial`;
        ctx.fillStyle = "#888";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("\u25C0", weightX + 10, y + H * 0.5);

        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR || "#DDD";
        ctx.font = `${Math.round(H * 0.6)}px Arial`;
        ctx.fillText(weight.toFixed(2), weightX + weightInnerW / 2, y + H * 0.5);

        ctx.fillStyle = "#888";
        ctx.font = `${Math.round(H * 0.5)}px Arial`;
        ctx.fillText("\u25B6", weightX + weightInnerW - 10, y + H * 0.5);
    }
}

function openComboDropdown(w, node, options, canvas) {
    const ref_window = canvas.getCanvasWindow();
    const values = options || w.options?.values || [];
    new LiteGraph.ContextMenu(
        values,
        {
            scale: Math.max(1, canvas.ds?.scale || 1),
            event: undefined,
            className: "dark",
            callback: (selected) => {
                w.value = selected;
                if (w.callback) w.callback(selected, null, node, [0, 0], w);
                node.setDirtyCanvas?.(true, true);
            },
        },
        ref_window
    );
}

function mouseComboWeightWidget(event, pos, node) {
    const w = this;
    if (event.type !== "pointerdown" && event.type !== "mousedown") return true;

    const isActive = w.value !== "none" && !isTagSeparatorValue(w.value);
    const margin = 15;
    const WEIGHT_W = isActive ? TAG_WEIGHT_AREA_WIDTH : 0;
    const comboW = node.size[0] - WEIGHT_W;
    const x = pos[0];

    // Weight area click
    if (isActive && x >= comboW) {
        const weightX = comboW;
        const weightInnerW = WEIGHT_W - margin;
        const relX = x - weightX;
        if (relX < 20) {
            w._tagWeight = Math.max(TAG_WEIGHT_MIN, Math.round(((w._tagWeight ?? 1.0) - TAG_WEIGHT_STEP) * 100) / 100);
        } else if (relX > weightInnerW - 20) {
            w._tagWeight = Math.min(TAG_WEIGHT_MAX, Math.round(((w._tagWeight ?? 1.0) + TAG_WEIGHT_STEP) * 100) / 100);
        }
        if (w._syncWeight) w._syncWeight(w._tagWeight);
        return true;
    }

    // Combo area click — open dropdown manually
    if (x >= margin && x < comboW - margin) {
        const canvas = app.canvas;
        if (canvas) openComboDropdown(w, node, w.options?.values, canvas);
        return true;
    }

    return true;
}

function inferTagGroup(node) {
    const tagWidget = (node.widgets || []).find((w) => !!w?.name && /_\d+$/.test(w.name));
    return tagWidget?.name.replace(/_\d+$/, "") || null;
}

function getTagWidgets(node, group) {
    // group: "focus" or "age" (or "age", "agescale" 등)
    return (node.widgets || []).filter((w) => isTagWidget(w, getTagPrefixes(node, group || node._tagGroup)));
}

function initTagCallbacks(node, group) {
    for (const w of getTagWidgets(node, group)) {
        w.callback = () => {
            if (isTagSeparatorValue(w.value)) {
                w.value = "none";
            }
            reconcileTagWidgets(node, group);
            const previewText = updatePreviewWidget(node, group);
            syncTextWidget(node, group, previewText);
        };
    }
}

function initSectionCallbacks(node, group) {
    const sectionsWidget = node.widgets?.find((w) => w.name === "sections");
    if (!sectionsWidget || !node._tagSectionValues) return;
    sectionsWidget.callback = () => {
        updateTagStateFromSections(node, group);
        const previewText = updatePreviewWidget(node, group);
        syncTextWidget(node, group, previewText);
    };

    const randomPickWidget = node.widgets?.find((w) => w.name === "random_pick");
    if (randomPickWidget) {
        randomPickWidget.callback = () => {
            const previewText = updatePreviewWidget(node, group);
            syncTextWidget(node, group, previewText);
        };
    }
}

function reconcileTagWidgets(node, group) {
    const options = node._tagOptions;
    const valueToParent = node._valueToParent || {};
    const baseGroup = getWidgetBaseGroup(group);
    if (!options) return;
    // 활성(non-"none") 값과 가중치를 순서대로 수집
    const activeEntries = getTagWidgets(node, group)
        .filter((w) => w.value !== "none" && !isTagSeparatorValue(w.value) && options.includes(w.value))
        .map((w) => {
            const idx = w.name.match(/_(\d+)$/)?.[1];
            const weightWidget = idx ? getWidgetByName(node, `weight_${idx}`) : null;
            return { value: w.value, weight: weightWidget?.value ?? (w._tagWeight ?? 1.0) };
        });
    const desiredCount = activeEntries.length + 1;
    const prefixes = getTagPrefixes(node, group);
    // 기존 tag 위젯과 weight 위젯 모두 제거 (reset 버튼은 남김)
    node.widgets = node.widgets.filter((w) => (!isTagWidget(w, prefixes) || w.name === "Reset") && !isWeightWidget(w));
    // 새 tag + hidden weight 위젯 생성
    const newWidgets = [];
    for (let i = 0; i < desiredCount; i++) {
        const entry = i < activeEntries.length ? activeEntries[i] : { value: "none", weight: 1.0 };
        const parent = group === "all" ? baseGroup : (valueToParent[entry.value] || group);
        const name = `${parent}_${i + 1}`;
        const w = node.addWidget(
            "combo",
            name,
            entry.value,
            () => {
                if (isTagSeparatorValue(w.value)) w.value = "none";
                reconcileTagWidgets(node, group);
                const previewText = updatePreviewWidget(node, group);
                syncTextWidget(node, group, previewText);
            },
            { values: options, serialize: true }
        );
        w.options = { ...(w.options || {}), values: options, serialize: true };
        node.widgets.pop();

        if (entry.value !== "none") {
            // 활성 태그: 커스텀 draw/mouse로 인라인 가중치 표시
            w._tagWeight = entry.weight;
            w.draw = drawComboWeightWidget;
            w.mouse = mouseComboWeightWidget;
            w.type = "ghtools_combo_weight";

            // hidden weight 위젯 (직렬화/백엔드 전달용)
            const hw = node.addWidget(
                "number", `weight_${i + 1}`, entry.weight,
                () => {},
                { min: 0.0, max: 3.0, step: 0.05, precision: 2, serialize: true }
            );
            hw.options = { ...(hw.options || {}), min: 0.0, max: 3.0, step: 0.05, precision: 2, serialize: true };
            hw.type = "hidden";
            hw.computeSize = () => [0, -4];
            node.widgets.pop();

            w._syncWeight = (val) => {
                w._tagWeight = val;
                hw.value = val;
                const previewText = updatePreviewWidget(node, group);
                syncTextWidget(node, group, previewText);
                app.graph.setDirtyCanvas(true);
            };

            newWidgets.push(w);
            newWidgets.push(hw);
        } else {
            newWidgets.push(w);
        }
    }
    // text 위젯 앞에 삽입
    const textIdx = node.widgets.findIndex((w) => w.name === "text");
    if (textIdx >= 0) {
        node.widgets.splice(textIdx, 0, ...newWidgets);
    } else {
        node.widgets.unshift(...newWidgets);
    }
    updatePreviewWidget(node, group);
    app.graph.setDirtyCanvas(true);
}

function resetTagWidgets(node) {
    getTagWidgets(node).forEach((w) => {
        if (w.name !== "Reset") {
            w.value = "none";
            w._tagWeight = 1.0;
        }
    });
    getWeightWidgets(node).forEach((w) => {
        w.value = 1.0;
    });
    const group = node._tagGroup || inferTagGroup(node) || Object.values(node._valueToParent || {})[0] || null;
    if (group) {
        reconcileTagWidgets(node, group);
        const previewText = updatePreviewWidget(node, group);
        syncTextWidget(node, group, previewText);
    }
}
