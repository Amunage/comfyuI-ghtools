import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function imageDataToUrl(data) {
    return api.apiURL(
        `/view?filename=${encodeURIComponent(data.filename)}&type=${data.type}&subfolder=${data.subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
    );
}

function fitHeight(node) {
    node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]]);
    node?.graph?.setDirtyCanvas(true, true);
}

async function pickFolder(folderPath) {
    try {
        const response = await api.fetchApi("/ghtools/image_autoloader_pick_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: folderPath || "" }),
        });
        return await response.json();
    } catch (error) {
        console.error("Image autoloader folder picker failed:", error);
        return { code: -1, error: error.message };
    }
}

async function refreshPreview(node, folderPath, previewWidget) {
    if (!folderPath || !previewWidget) {
        previewWidget?.setStatus("No folder selected");
        node?.setDirtyCanvas(true, true);
        return;
    }

    previewWidget.setStatus("Loading...");
    node.setDirtyCanvas(true, true);

    try {
        const response = await api.fetchApi("/ghtools/image_autoloader_preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: folderPath }),
        });
        const result = await response.json();

        if (result?.code !== 1 || !result.image) {
            previewWidget.value = { images: [] };
            previewWidget.setStatus(result?.error || "No preview image");
            node.setDirtyCanvas(true, true);
            return;
        }

        previewWidget.value = {
            images: [
                {
                    ...result.image,
                    url: imageDataToUrl(result.image),
                },
            ],
        };
        previewWidget.setStatus(result.source_path || "Preview updated");
        node.setDirtyCanvas(true, true);
    } catch (error) {
        console.error("Image autoloader preview refresh failed:", error);
        previewWidget.value = { images: [] };
        previewWidget.setStatus(error.message || "Preview refresh failed");
        node.setDirtyCanvas(true, true);
    }
}

app.registerExtension({
    name: "gh.ImageAutoloader",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "GHImageAutoloader") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            onNodeCreated?.apply(this, arguments);

            this.imgs = [];
            this.serialize_widgets = true;

            const folderPathWidget = this.widgets?.find((widget) => widget.name === "folder_path");
            if (!folderPathWidget || this.imageAutoloaderButtons || this.imageAutoloaderPreview) {
                return;
            }

            this.imageAutoloaderButtons = this.addCustomWidget(
                new GHImageAutoloaderButtonsWidget("gh_image_autoloader_buttons", this, folderPathWidget)
            );
            this.imageAutoloaderPreview = this.addCustomWidget(
                new GHImageAutoloaderPreviewWidget("gh_image_autoloader_preview", this)
            );

            const widgets = this.widgets || [];
            const folderIdx = widgets.indexOf(folderPathWidget);
            const buttonIdx = widgets.indexOf(this.imageAutoloaderButtons);
            const previewIdx = widgets.indexOf(this.imageAutoloaderPreview);

            if (folderIdx >= 0 && buttonIdx >= 0 && buttonIdx !== folderIdx + 1) {
                widgets.splice(buttonIdx, 1);
                widgets.splice(folderIdx + 1, 0, this.imageAutoloaderButtons);
            }

            const latestButtonIdx = widgets.indexOf(this.imageAutoloaderButtons);
            const latestPreviewIdx = widgets.indexOf(this.imageAutoloaderPreview);
            if (latestButtonIdx >= 0 && latestPreviewIdx >= 0 && latestPreviewIdx !== latestButtonIdx + 1) {
                widgets.splice(latestPreviewIdx, 1);
                widgets.splice(latestButtonIdx + 1, 0, this.imageAutoloaderPreview);
            }

            this.imageAutoloaderPreview.setStatus("No preview image");

            const originalOnExecuted = this.onExecuted;
            this.onExecuted = function(output) {
                originalOnExecuted?.apply(this, arguments);

                const images = (output?.images || []).map((image) => ({
                    ...image,
                    url: imageDataToUrl(image),
                }));

                if (this.imageAutoloaderPreview) {
                    this.imageAutoloaderPreview.value = { images };
                    this.imageAutoloaderPreview.setStatus(images.length ? "Preview updated" : "No preview image");
                }

                this.imgs = [];
                this.setDirtyCanvas(true, true);
            };

            this.onDrawBackground = function() {
                // preview is rendered by the custom preview widget
            };

            fitHeight(this);
        };
    },
});

class GHImageAutoloaderButtonsWidget {
    constructor(name, node, folderPathWidget) {
        this.name = name;
        this.type = "custom";
        this.node = node;
        this.folderPathWidget = folderPathWidget;
        this.options = { serialize: false };
        this.hitAreas = {};
        this.downedHitAreasForClick = [];
        this.mouseDowned = null;
        this.isHandlingClick = false;
    }

    clickWasWithinBounds(pos, bounds) {
        const [x, y, width, height] = bounds;
        return pos[0] >= x && pos[0] <= x + width && pos[1] >= y && pos[1] <= y + height;
    }

    mouse(event, pos, node) {
        if (event.type === "pointerdown") {
            this.mouseDowned = [...pos];
            this.downedHitAreasForClick = [];

            for (const part of Object.values(this.hitAreas)) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    part.wasMouseClickedAndIsOver = true;
                    if (part.onClick) {
                        this.downedHitAreasForClick.push(part);
                    }
                }
            }

            return this.downedHitAreasForClick.length > 0;
        }

        if (event.type === "pointermove") {
            if (!this.mouseDowned) {
                return false;
            }

            for (const part of this.downedHitAreasForClick) {
                part.wasMouseClickedAndIsOver = this.clickWasWithinBounds(pos, part.bounds);
            }
            node.setDirtyCanvas(true, false);
            return true;
        }

        if (event.type === "pointerup") {
            if (!this.mouseDowned) {
                return false;
            }

            const clickedParts = [...this.downedHitAreasForClick];
            this.mouseDowned = null;
            this.downedHitAreasForClick = [];

            for (const part of Object.values(this.hitAreas)) {
                part.wasMouseClickedAndIsOver = false;
            }

            for (const part of clickedParts) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    part.onClick?.call(this, event, pos, node, part);
                }
            }

            node.setDirtyCanvas(true, false);
            return clickedParts.length > 0;
        }

        return false;
    }

    draw(ctx, node, width, y) {
        this.hitAreas = {};

        const labels = [
            { key: "refresh", text: "Refresh" },
            { key: "folder", text: "Folder" },
        ];

        const horizontalMargin = 8;
        const spacing = 4;
        const buttonHeight = 20;
        const totalSpacing = spacing * (labels.length - 1);
        const buttonWidth = (node.size[0] - horizontalMargin * 2 - totalSpacing) / labels.length;
        let buttonX = horizontalMargin;

        for (const item of labels) {
            const isPressed = this.downedHitAreasForClick.some(
                (part) => part.key === item.key && part.wasMouseClickedAndIsOver
            );

            ctx.fillStyle = isPressed ? "rgba(95, 145, 95, 1)" : "rgba(35, 35, 35, 1)";
            ctx.strokeStyle = "rgba(100, 100, 100, 1)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(buttonX, y, buttonWidth, buttonHeight, 5);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = "rgba(230, 230, 230, 1)";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.font = "12px Arial";
            ctx.fillText(item.text, buttonX + buttonWidth / 2, y + buttonHeight / 2);

            this.hitAreas[item.key] = {
                key: item.key,
                bounds: [buttonX, y, buttonWidth, buttonHeight],
                data: item.key,
                onClick: this.onActionButtonClick.bind(this),
            };

            buttonX += buttonWidth + spacing;
        }
    }

    async onActionButtonClick(event, pos, node, bounds) {
        if (this.isHandlingClick) {
            return;
        }

        const action = bounds?.data;
        if (!action) {
            return;
        }

        this.isHandlingClick = true;

        try {
            if (action === "refresh") {
                if (this.folderPathWidget?.value) {
                    await refreshPreview(node, this.folderPathWidget.value, node.imageAutoloaderPreview);
                }
                return;
            }

            if (action === "folder") {
                const result = await pickFolder(this.folderPathWidget?.value || "");
                if (result?.code !== 1 || !result.folder_path) {
                    return;
                }

                this.folderPathWidget.value = result.folder_path;
                this.folderPathWidget.callback?.(result.folder_path, node, this.folderPathWidget);
                node.setDirtyCanvas(true, true);
                await refreshPreview(node, result.folder_path, node.imageAutoloaderPreview);
            }
        } finally {
            this.isHandlingClick = false;
        }
    }

    computeSize(width) {
        return [width, 28];
    }

    serializeValue() {
        return undefined;
    }
}

class GHImageAutoloaderPreviewWidget {
    constructor(name, node) {
        this.name = name;
        this.type = "custom";
        this.node = node;
        this.options = { serialize: false };
        this._value = { images: [] };
        this.imageObj = null;
        this.statusText = "No preview image";
    }

    set value(v) {
        const images = Array.isArray(v) ? v : v?.images || [];
        this._value.images = images;

        if (!images.length) {
            this.imageObj = null;
            return;
        }

        const nextImage = images[0];
        const nextUrl = nextImage.url || imageDataToUrl(nextImage);
        if (!this.imageObj || this.imageObj.src !== nextUrl) {
            this.imageObj = new Image();
            this.imageObj.src = nextUrl;
        }
    }

    get value() {
        return this._value;
    }

    setStatus(text) {
        this.statusText = text || "";
    }

    draw(ctx, node, width, y) {
        const padding = 8;
        const previewHeight = Math.max(220, node.size[1] - y - padding);
        const boxX = padding;
        const boxY = y;
        const boxWidth = node.size[0] - padding * 2;
        const boxHeight = previewHeight;

        if (this.imageObj?.naturalWidth && this.imageObj?.naturalHeight) {
            const imageAspect = this.imageObj.naturalWidth / this.imageObj.naturalHeight;
            const boxAspect = boxWidth / boxHeight;
            let drawWidth = boxWidth;
            let drawHeight = boxHeight;

            if (imageAspect > boxAspect) {
                drawHeight = boxWidth / imageAspect;
            } else {
                drawWidth = boxHeight * imageAspect;
            }

            const drawX = boxX + (boxWidth - drawWidth) / 2;
            const drawY = boxY + (boxHeight - drawHeight) / 2;
            ctx.drawImage(this.imageObj, drawX, drawY, drawWidth, drawHeight);
            return;
        }

        ctx.fillStyle = "rgba(180, 180, 180, 0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.font = "12px Arial";
        ctx.fillText(this.statusText || "No preview image", boxX + boxWidth / 2, boxY + boxHeight / 2);
    }

    computeSize(width) {
        return [width, 220];
    }

    serializeValue() {
        return undefined;
    }
}