import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function imageDataToUrl(data) {
    return api.apiURL(
        `/view?filename=${encodeURIComponent(data.filename)}&type=${data.type}&subfolder=${data.subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
    );
}

async function sendCropMessage(nodeId, action, crop) {
    try {
        const body = { node_id: nodeId, action };
        if (crop) body.crop = crop;
        const response = await api.fetchApi("/ghtools/image_crop_message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        return await response.json();
    } catch (error) {
        console.error("Image crop message failed:", error);
        return { code: -1, error: error.message };
    }
}

// ─── Widget ──────────────────────────────────────────────────────────
class GHImageCropWidget {
    constructor(name, node) {
        this.name = name;
        this.type = "custom";
        this.node = node;
        this.y = 0;
        this.buttonsBottomY = 0;

        this._value = { images: [] };
        this.imageObj = null;
        this.imageData = null;

        // drag state (node-local coordinates)
        this.isDragging = false;
        this.dragStart = null;
        this.dragEnd = null;
        // confirmed selection rect {x, y, w, h} in node coords
        this.selectionRect = null;

        // interaction state: 'none' | 'draw' | 'move' | 'resize'
        this.interactionMode = 'none';
        this.resizeAnchor = null;
        this.moveStartPos = null;
        this.moveStartRect = null;

        this.hitAreas = {};
    }

    /* ── value property ─────────────────────────────────── */
    set value(v) {
        const images = Array.isArray(v) ? v : v?.images || [];
        this._value.images = images;
        this.selectionRect = null;
        this.isDragging = false;
        this.interactionMode = 'none';
        if (images.length > 0) {
            const url = images[0].url || imageDataToUrl(images[0]);
            if (!this.imageObj || this.imageObj.src !== url) {
                this.imageObj = new Image();
                this.imageObj.src = url;
                this.imageData = images[0];
            }
        }
    }
    get value() {
        return this._value;
    }

    /* ── helpers ─────────────────────────────────────────── */
    get keepRatio() {
        const w = this.node.widgets?.find((w) => w.name === "keep_ratio");
        return w ? w.value : false;
    }

    _getImageLayout() {
        if (!this.imageObj?.naturalWidth) return null;
        const nodeWidth = this.node.size[0];
        const nodeHeight = this.node.size[1];
        const canvasH = nodeHeight - this.buttonsBottomY;
        if (canvasH <= 0) return null;
        const imgAspect = this.imageObj.naturalWidth / this.imageObj.naturalHeight;
        const canvasAspect = nodeWidth / canvasH;

        let drawW, drawH;
        if (imgAspect > canvasAspect) {
            drawW = nodeWidth;
            drawH = nodeWidth / imgAspect;
        } else {
            drawH = canvasH;
            drawW = canvasH * imgAspect;
        }
        const offsetX = (nodeWidth - drawW) / 2;
        const offsetY = this.buttonsBottomY + (canvasH - drawH) / 2;
        return { drawW, drawH, offsetX, offsetY };
    }

    _canvasToImage(cx, cy) {
        const layout = this._getImageLayout();
        if (!layout) return null;
        const { drawW, drawH, offsetX, offsetY } = layout;
        const scaleX = this.imageObj.naturalWidth / drawW;
        const scaleY = this.imageObj.naturalHeight / drawH;
        return {
            x: (cx - offsetX) * scaleX,
            y: (cy - offsetY) * scaleY,
        };
    }

    _isInBounds(pos, bounds) {
        const [bx, by, bw, bh] = bounds;
        return pos[0] >= bx && pos[0] <= bx + bw && pos[1] >= by && pos[1] <= by + bh;
    }

    _clampToImage(pos) {
        const layout = this._getImageLayout();
        if (!layout) return pos;
        const { drawW, drawH, offsetX, offsetY } = layout;
        return [
            Math.max(offsetX, Math.min(pos[0], offsetX + drawW)),
            Math.max(offsetY, Math.min(pos[1], offsetY + drawH)),
        ];
    }

    _applyRatio(start, end) {
        if (!this.keepRatio || !this.imageObj?.naturalWidth || !this.imageObj?.naturalHeight) {
            return end;
        }
        const layout = this._getImageLayout();
        if (!layout) return end;
        const { drawW, drawH, offsetX, offsetY } = layout;

        let dx = end[0] - start[0];
        let dy = end[1] - start[1];
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        const canvasRatio = drawW / drawH;

        let newDx, newDy;
        if (absDx / canvasRatio >= absDy) {
            newDx = dx;
            newDy = Math.sign(dy || 1) * (absDx / canvasRatio);
        } else {
            newDy = dy;
            newDx = Math.sign(dx || 1) * (absDy * canvasRatio);
        }

        let ex = Math.max(offsetX, Math.min(start[0] + newDx, offsetX + drawW));
        let ey = Math.max(offsetY, Math.min(start[1] + newDy, offsetY + drawH));
        return [ex, ey];
    }

    /* ── hit-test helpers ────────────────────────────────── */
    _hitTestHandle(pos) {
        if (!this.selectionRect) return null;
        const r = this.selectionRect;
        const corners = [
            ['tl', r.x, r.y],
            ['tr', r.x + r.w, r.y],
            ['bl', r.x, r.y + r.h],
            ['br', r.x + r.w, r.y + r.h],
        ];
        const threshold = 10;
        for (const [key, hx, hy] of corners) {
            if (Math.abs(pos[0] - hx) <= threshold && Math.abs(pos[1] - hy) <= threshold) {
                return key;
            }
        }
        return null;
    }

    _isInsideSelection(pos) {
        if (!this.selectionRect) return false;
        const r = this.selectionRect;
        return pos[0] >= r.x && pos[0] <= r.x + r.w && pos[1] >= r.y && pos[1] <= r.y + r.h;
    }

    /* ── node-level mouse handlers ───────────────────────── */
    handleMouseDown(pos) {
        if (!this.node.isWaiting) return false;

        for (const area of Object.values(this.hitAreas)) {
            if (this._isInBounds(pos, area.bounds)) {
                if (area.onClick) area.onClick(area);
                this.node.setDirtyCanvas(true, false);
                return true;
            }
        }
        if (pos[1] <= this.buttonsBottomY || !this.imageObj?.naturalWidth) return false;

        // If selection exists: resize handle or move
        if (this.selectionRect) {
            const handle = this._hitTestHandle(pos);
            if (handle) {
                this.interactionMode = 'resize';
                const r = this.selectionRect;
                const anchors = {
                    'tl': [r.x + r.w, r.y + r.h],
                    'tr': [r.x, r.y + r.h],
                    'bl': [r.x + r.w, r.y],
                    'br': [r.x, r.y],
                };
                this.resizeAnchor = anchors[handle];
                this.dragStart = this.resizeAnchor;
                this.dragEnd = this._clampToImage(pos);
                this.node.setDirtyCanvas(true, false);
                return true;
            }

            if (this._isInsideSelection(pos)) {
                this.interactionMode = 'move';
                this.moveStartPos = [pos[0], pos[1]];
                this.moveStartRect = { ...this.selectionRect };
                this.node.setDirtyCanvas(true, false);
                return true;
            }

            return true; // capture outside clicks to prevent node drag
        }

        // No selection: draw new
        const clamped = this._clampToImage(pos);
        this.interactionMode = 'draw';
        this.isDragging = true;
        this.dragStart = clamped;
        this.dragEnd = clamped;
        this.node.setDirtyCanvas(true, false);
        return true;
    }

    handleMouseMove(pos, event) {
        // If mouse button already released (missed mouseUp), end interaction
        if (this.interactionMode !== 'none' && event && event.buttons === 0) {
            this.handleMouseUp(pos);
            return true;
        }

        if (this.interactionMode === 'draw' && this.isDragging) {
            this.dragEnd = this._applyRatio(this.dragStart, this._clampToImage(pos));
            this.node.setDirtyCanvas(true, false);
            return true;
        }

        if (this.interactionMode === 'resize') {
            this.dragEnd = this._applyRatio(this.dragStart, this._clampToImage(pos));
            const x1 = Math.min(this.dragStart[0], this.dragEnd[0]);
            const y1 = Math.min(this.dragStart[1], this.dragEnd[1]);
            const x2 = Math.max(this.dragStart[0], this.dragEnd[0]);
            const y2 = Math.max(this.dragStart[1], this.dragEnd[1]);
            if (x2 - x1 > 3 && y2 - y1 > 3) {
                this.selectionRect = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
            }
            this.node.setDirtyCanvas(true, false);
            return true;
        }

        if (this.interactionMode === 'move') {
            const dx = pos[0] - this.moveStartPos[0];
            const dy = pos[1] - this.moveStartPos[1];
            const layout = this._getImageLayout();
            if (layout) {
                const { drawW, drawH, offsetX, offsetY } = layout;
                const r = this.moveStartRect;
                let newX = r.x + dx;
                let newY = r.y + dy;
                newX = Math.max(offsetX, Math.min(newX, offsetX + drawW - r.w));
                newY = Math.max(offsetY, Math.min(newY, offsetY + drawH - r.h));
                this.selectionRect = { x: newX, y: newY, w: r.w, h: r.h };
            }
            this.node.setDirtyCanvas(true, false);
            return true;
        }

        return false;
    }

    handleMouseUp(pos) {
        if (this.interactionMode === 'draw' && this.isDragging) {
            this.isDragging = false;
            this.dragEnd = this._applyRatio(this.dragStart, this._clampToImage(pos));
            const x1 = Math.min(this.dragStart[0], this.dragEnd[0]);
            const y1 = Math.min(this.dragStart[1], this.dragEnd[1]);
            const x2 = Math.max(this.dragStart[0], this.dragEnd[0]);
            const y2 = Math.max(this.dragStart[1], this.dragEnd[1]);
            if (x2 - x1 > 3 && y2 - y1 > 3) {
                this.selectionRect = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
            }
            this.interactionMode = 'none';
            this.node.setDirtyCanvas(true, false);
            return true;
        }

        if (this.interactionMode === 'resize' || this.interactionMode === 'move') {
            this.interactionMode = 'none';
            this.node.setDirtyCanvas(true, false);
            return true;
        }

        return false;
    }

    mouse(event, pos, node) {
        if (!node.isWaiting) return false;
        if (event.type === "pointerdown") {
            for (const area of Object.values(this.hitAreas)) {
                if (this._isInBounds(pos, area.bounds)) {
                    if (area.onClick) area.onClick(area);
                    node.setDirtyCanvas(true, false);
                    return true;
                }
            }
        }
        return false;
    }

    /* ── drawing ─────────────────────────────────────────── */
    draw(ctx, node, width, y) {
        this.y = y;
        this.hitAreas = {};
        const btnBottom = this._drawActionButtons(ctx, node, y);
        this.buttonsBottomY = btnBottom;
        this._drawPreview(ctx, node, btnBottom);
        this._drawSelection(ctx);
        this._drawCropInfo(ctx, node);
    }

    _drawActionButtons(ctx, node, y) {
        const labels = [
            { key: "confirm", text: "Confirm" },
            { key: "reset", text: "Reset" },
            { key: "cancel", text: "Cancel" },
        ];

        const hMargin = 8;
        const spacing = 4;
        const btnH = 22;
        const totalSpacing = spacing * (labels.length - 1);
        const btnW = (node.size[0] - hMargin * 2 - totalSpacing) / labels.length;
        let btnX = hMargin;

        for (const item of labels) {
            const isWaiting = !!node.isWaiting;
            const alpha = isWaiting ? 1 : 0.45;

            ctx.fillStyle = `rgba(35, 35, 35, ${alpha})`;
            ctx.strokeStyle = `rgba(100, 100, 100, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(btnX, y, btnW, btnH, 5);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = `rgba(230, 230, 230, ${alpha})`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.font = "12px Arial";
            ctx.fillText(item.text, btnX + btnW / 2, y + btnH / 2);

            this.hitAreas[item.key] = {
                key: item.key,
                bounds: [btnX, y, btnW, btnH],
                onClick: this._onButtonClick.bind(this),
            };

            btnX += btnW + spacing;
        }
        return y + btnH + 6;
    }

    _drawPreview(ctx, node, y) {
        if (!this.imageObj?.naturalWidth) return;
        const layout = this._getImageLayout();
        if (!layout) return;
        const { drawW, drawH, offsetX, offsetY } = layout;
        ctx.drawImage(this.imageObj, offsetX, offsetY, drawW, drawH);
    }

    _drawSelection(ctx) {
        let rect = null;
        if (this.isDragging && this.dragStart && this.dragEnd) {
            const x1 = Math.min(this.dragStart[0], this.dragEnd[0]);
            const y1 = Math.min(this.dragStart[1], this.dragEnd[1]);
            const x2 = Math.max(this.dragStart[0], this.dragEnd[0]);
            const y2 = Math.max(this.dragStart[1], this.dragEnd[1]);
            rect = { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
        } else if (this.selectionRect) {
            rect = this.selectionRect;
        }
        if (!rect || rect.w < 2 || rect.h < 2) return;

        // dim area outside selection
        ctx.save();
        ctx.fillStyle = "rgba(0,0,0,0.45)";
        const layout = this._getImageLayout();
        if (layout) {
            const { drawW, drawH, offsetX, offsetY } = layout;
            // top
            ctx.fillRect(offsetX, offsetY, drawW, Math.max(0, rect.y - offsetY));
            // bottom
            const bottomY = rect.y + rect.h;
            ctx.fillRect(offsetX, bottomY, drawW, Math.max(0, offsetY + drawH - bottomY));
            // left
            ctx.fillRect(offsetX, rect.y, Math.max(0, rect.x - offsetX), rect.h);
            // right
            const rightX = rect.x + rect.w;
            ctx.fillRect(rightX, rect.y, Math.max(0, offsetX + drawW - rightX), rect.h);
        }

        // selection border
        ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 3]);
        ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
        ctx.setLineDash([]);

        // corner handles
        const handleSize = 8;
        ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
        ctx.strokeStyle = "rgba(0, 0, 0, 0.6)";
        ctx.lineWidth = 1;
        for (const [cx, cy] of [
            [rect.x, rect.y],
            [rect.x + rect.w, rect.y],
            [rect.x, rect.y + rect.h],
            [rect.x + rect.w, rect.y + rect.h],
        ]) {
            ctx.fillRect(cx - handleSize / 2, cy - handleSize / 2, handleSize, handleSize);
            ctx.strokeRect(cx - handleSize / 2, cy - handleSize / 2, handleSize, handleSize);
        }
        ctx.restore();
    }

    _drawCropInfo(ctx, node) {
        const rect = this.selectionRect;
        if (!rect || !this.imageObj?.naturalWidth) return;
        const tl = this._canvasToImage(rect.x, rect.y);
        const br = this._canvasToImage(rect.x + rect.w, rect.y + rect.h);
        if (!tl || !br) return;

        const imgW = Math.round(Math.abs(br.x - tl.x));
        const imgH = Math.round(Math.abs(br.y - tl.y));
        const text = `${imgW} x ${imgH}`;

        ctx.save();
        ctx.font = "11px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";

        const tx = rect.x + rect.w / 2;
        const ty = rect.y - 4;

        ctx.fillStyle = "rgba(0,0,0,0.6)";
        const tw = ctx.measureText(text).width + 8;
        ctx.fillRect(tx - tw / 2, ty - 14, tw, 16);

        ctx.fillStyle = "#fff";
        ctx.fillText(text, tx, ty);
        ctx.restore();
    }

    /* ── button actions ──────────────────────────────────── */
    async _onButtonClick(bounds) {
        const action = bounds?.key;
        if (!action) return;
        const node = this.node;

        if (action === "reset") {
            this.selectionRect = null;
            this.isDragging = false;
            this.interactionMode = 'none';
            node.setDirtyCanvas(true, false);
            return;
        }

        if (!node.isWaiting) return;

        if (action === "confirm") {
            if (!this.imageObj?.naturalWidth) return;

            let cropX, cropY, cropW, cropH;
            if (this.selectionRect) {
                const tl = this._canvasToImage(this.selectionRect.x, this.selectionRect.y);
                const br = this._canvasToImage(
                    this.selectionRect.x + this.selectionRect.w,
                    this.selectionRect.y + this.selectionRect.h
                );
                if (!tl || !br) return;
                cropX = Math.max(0, Math.round(Math.min(tl.x, br.x)));
                cropY = Math.max(0, Math.round(Math.min(tl.y, br.y)));
                cropW = Math.round(Math.abs(br.x - tl.x));
                cropH = Math.round(Math.abs(br.y - tl.y));
            } else {
                cropX = 0;
                cropY = 0;
                cropW = this.imageObj.naturalWidth;
                cropH = this.imageObj.naturalHeight;
            }

            const result = await sendCropMessage(node.id, "crop", {
                x: cropX,
                y: cropY,
                width: cropW,
                height: cropH,
            });
            if (result?.code === 1) {
                node.isWaiting = false;
                node.setDirtyCanvas(true, true);
            }
            return;
        }

        if (action === "cancel") {
            const result = await sendCropMessage(node.id, "cancel");
            if (result?.code === 1) {
                node.isWaiting = false;
                node.setDirtyCanvas(true, true);
            }
        }
    }

    /* ── serialisation ───────────────────────────────────── */
    computeSize(width) {
        return [width, 22];
    }

    serializeValue() {
        return {
            images: this._value.images.map((d) => {
                const copy = { ...d };
                delete copy.img;
                return copy;
            }),
        };
    }
}

// ─── Extension registration ──────────────────────────────────────────
app.registerExtension({
    name: "gh.ImageCrop",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "GHImageCrop") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            this.imgs = [];
            this.isWaiting = false;
            this.serialize_widgets = true;

            // Native ComfyUI toggle widget for keep_ratio
            const keepRatioWidget = this.addWidget("toggle", "keep_ratio", false, () => {
                this.setDirtyCanvas(true, false);
            });
            keepRatioWidget.serializeValue = () => keepRatioWidget.value;

            this.cropWidget = this.addCustomWidget(new GHImageCropWidget("gh_crop", this));
            this.setSize([340, 440]);
            this.setDirtyCanvas(true, true);
        };

        // Node-level mouse handlers — return true to prevent node dragging
        nodeType.prototype.onMouseDown = function (event, pos, canvas) {
            if (this.cropWidget) {
                return this.cropWidget.handleMouseDown(pos);
            }
            return false;
        };

        nodeType.prototype.onMouseMove = function (event, pos, canvas) {
            if (this.cropWidget) {
                return this.cropWidget.handleMouseMove(pos, event);
            }
            return false;
        };

        nodeType.prototype.onMouseUp = function (event, pos, canvas) {
            if (this.cropWidget) {
                return this.cropWidget.handleMouseUp(pos);
            }
            return false;
        };

        nodeType.prototype.onSerialize = function (serialised) {
            for (let [index, wv] of (serialised.widgets_values || []).entries()) {
                if (this.widgets[index]?.name === "gh_crop") {
                    serialised.widgets_values[index] = this.widgets[index].value.images.map((d) => {
                        const copy = { ...d };
                        delete copy.img;
                        return copy;
                    });
                }
            }
        };

        nodeType.prototype.onDrawBackground = function () {
            // custom widget draws everything
        };

        nodeType.prototype.onExecuted = function (output) {
            if (!this.cropWidget) return;
            const images = (output.images || []).map((d) => ({
                ...d,
                url: imageDataToUrl(d),
            }));
            this.cropWidget.value = { images };
            this.imgs = [];
            this.setDirtyCanvas(true, true);
        };
    },

    setup() {
        const TYPE = "GHImageCrop";

        api.addEventListener("ghtools-image-crop-images", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (!node || node.type !== TYPE || !node.cropWidget) return;
            const images = (event.detail.images || []).map((d) => ({
                ...d,
                url: imageDataToUrl(d),
            }));
            node.cropWidget.value = { images };
            node.setDirtyCanvas(true, true);
        });

        api.addEventListener("ghtools-image-crop-waiting", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (node && node.type === TYPE) {
                node.isWaiting = true;
                node.setDirtyCanvas(true, true);
            }
        });

        api.addEventListener("ghtools-image-crop-keep-selection", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (node && node.type === TYPE) {
                node.isWaiting = false;
                node.setDirtyCanvas(true, true);
            }
        });

        for (const eventName of [
            "execution_start",
            "execution_cached",
            "execution_error",
            "execution_interrupted",
        ]) {
            api.addEventListener(eventName, () => {
                app.graph._nodes.forEach((node) => {
                    if (node.type === TYPE) {
                        node.isWaiting = false;
                        node.setDirtyCanvas(true, true);
                    }
                });
            });
        }
    },
});
