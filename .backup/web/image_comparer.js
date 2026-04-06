import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function imageDataToUrl(data) {
    return api.apiURL(`/view?filename=${encodeURIComponent(data.filename)}&type=${data.type}&subfolder=${data.subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`);
}

function measureText(ctx, text) {
    return ctx.measureText(text).width;
}

async function sendComparerMessage(nodeId, action) {
    try {
        const response = await api.fetchApi("/ghtools/image_comparer_message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ node_id: nodeId, action }),
        });
        return await response.json();
    } catch (error) {
        console.error("Image comparer message failed:", error);
        return { code: -1, error: error.message };
    }
}

function buildImagesFromOutput(output) {
    if ("images" in output) {
        return (output.images || []).map((d, i) => ({
            name: i === 0 ? "A" : "B",
            selected: true,
            url: imageDataToUrl(d),
        }));
    }

    output.a_images = output.a_images || [];
    output.b_images = output.b_images || [];
    const imagesToChoose = [];
    const multiple = output.a_images.length + output.b_images.length > 2;

    for (const [i, d] of output.a_images.entries()) {
        imagesToChoose.push({
            name: output.a_images.length > 1 || multiple ? `A${i + 1}` : "A",
            selected: i === 0,
            url: imageDataToUrl(d),
        });
    }

    for (const [i, d] of output.b_images.entries()) {
        imagesToChoose.push({
            name: output.b_images.length > 1 || multiple ? `B${i + 1}` : "B",
            selected: i === 0,
            url: imageDataToUrl(d),
        });
    }

    return imagesToChoose;
}

app.registerExtension({
    name: "gh.ImageComparer",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "GHImageComparer") {
            // comparer_mode 프로퍼티를 드롭다운으로 표시
            nodeType["@comparer_mode"] = {
                type: "combo",
                values: ["Slide", "Click"],
            };

            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);
                
                this.imageIndex = 0;
                this.imgs = [];
                this.isWaiting = false;
                this.serialize_widgets = true;
                this.isPointerDown = false;
                this.isPointerOver = false;
                this.pointerOverPos = [0, 0];
                this.properties = this.properties || {};
                this.properties["comparer_mode"] = this.properties["comparer_mode"] || "Slide";
                
                this.canvasWidget = this.addCustomWidget(new GHImageComparerWidget("gh_comparer", this));
                this.setSize(this.computeSize());
                this.setDirtyCanvas(true, true);
            };

            nodeType.prototype.onSerialize = function(serialised) {
                for (let [index, widget_value] of (serialised.widgets_values || []).entries()) {
                    if (this.widgets[index]?.name === "gh_comparer") {
                        serialised.widgets_values[index] = this.widgets[index].value.images.map((d) => {
                            d = { ...d };
                            delete d.img;
                            return d;
                        });
                    }
                }
            };

            nodeType.prototype.setIsPointerDown = function(down = this.isPointerDown) {
                const newIsDown = down && !!app.canvas.pointer_is_down;
                if (this.isPointerDown !== newIsDown) {
                    this.isPointerDown = newIsDown;
                    this.setDirtyCanvas(true, false);
                }
                this.imageIndex = this.isPointerDown ? 1 : 0;
                if (this.isPointerDown) {
                    requestAnimationFrame(() => {
                        this.setIsPointerDown();
                    });
                }
            };

            nodeType.prototype.onMouseDown = function(event, pos, canvas) {
                this.setIsPointerDown(true);
                return false;
            };

            nodeType.prototype.onMouseEnter = function(event) {
                this.setIsPointerDown(!!app.canvas.pointer_is_down);
                this.isPointerOver = true;
            };

            nodeType.prototype.onMouseLeave = function(event) {
                this.setIsPointerDown(false);
                this.isPointerOver = false;
            };

            nodeType.prototype.onMouseMove = function(event, pos, canvas) {
                this.pointerOverPos = [...pos];
                this.imageIndex = this.pointerOverPos[0] > this.size[0] / 2 ? 1 : 0;
                this.setDirtyCanvas(true, false);
            };

            // ComfyUI의 기본 PreviewImage 렌더링 비활성화
            nodeType.prototype.onDrawBackground = function(ctx) {
                // 아무것도 그리지 않음 - 커스텀 위젯이 이미지를 그림
            };

            // imgs 배열을 비워서 ComfyUI가 이미지 UI를 표시하지 않도록 함
            nodeType.prototype.onExecuted = function(output) {
                // 먼저 canvasWidget 초기화 확인
                if (!this.canvasWidget) return;

                this.canvasWidget.value = { images: buildImagesFromOutput(output) };
                this.isWaiting = false;
                
                // ComfyUI의 기본 이미지 배열을 비워서 기본 UI가 표시되지 않도록 함
                // (이미지는 커스텀 위젯에서 관리)
                this.imgs = [];
                this.setDirtyCanvas(true, true);
            };

            const origGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function(canvas, options) {
                origGetExtraMenuOptions?.apply(this, arguments);
                
                const imageIndex = this.pointerOverPos[0] <= this.size[0] / 2 ? 0 : 1;
                const image = this.canvasWidget?.selected?.[imageIndex];
                if (image?.img) {
                    options.unshift(
                        {
                            content: "Open Image",
                            callback: () => window.open(image.url, "_blank"),
                        },
                        {
                            content: "Save Image",
                            callback: () => {
                                const a = document.createElement("a");
                                a.href = image.url;
                                a.download = image.name || "image.png";
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                            },
                        }
                    );
                }
            };
        }
    },
    setup() {
        const TYPE = "GHImageComparer";

        api.addEventListener("ghtools-image-comparer-images", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (!node || node.type !== TYPE || !node.canvasWidget) {
                return;
            }

            const output = {
                a_images: event.detail.a_images || [],
                b_images: event.detail.b_images || [],
            };
            node.canvasWidget.value = { images: buildImagesFromOutput(output) };
            node.setDirtyCanvas(true, true);
        });

        api.addEventListener("ghtools-image-comparer-waiting", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (node && node.type === TYPE) {
                node.isWaiting = true;
                node.setDirtyCanvas(true, true);
            }
        });

        api.addEventListener("ghtools-image-comparer-keep-selection", (event) => {
            const node = app.graph._nodes_by_id[event.detail.id];
            if (node && node.type === TYPE) {
                node.isWaiting = false;
                node.setDirtyCanvas(true, true);
            }
        });

        api.addEventListener("ghtools-image-comparer-retry", () => {
            setTimeout(() => {
                app.queuePrompt(0, 1);
            }, 100);
        });

        for (const eventName of ["execution_start", "execution_cached", "execution_error", "execution_interrupted"]) {
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

class GHImageComparerWidget {
    constructor(name, node) {
        this.name = name;
        this.type = "custom";
        this.hitAreas = {};
        this.selected = [];
        this._value = { images: [] };
        this.node = node;
        this.y = 0;
        this.last_y = 0;
        this.mouseDowned = null;
        this.isMouseDownedAndOver = false;
        this.downedHitAreasForMove = [];
        this.downedHitAreasForClick = [];
    }

    set value(v) {
        let cleanedVal;
        if (Array.isArray(v)) {
            cleanedVal = v.map((d, i) => {
                if (!d || typeof d === "string") {
                    d = { url: d, name: i == 0 ? "A" : "B", selected: true };
                }
                return d;
            });
        }
        else {
            cleanedVal = v.images || [];
        }
        if (cleanedVal.length > 2) {
            const hasAAndB = cleanedVal.some((i) => i.name.startsWith("A")) &&
                cleanedVal.some((i) => i.name.startsWith("B"));
            if (!hasAAndB) {
                cleanedVal = [cleanedVal[0], cleanedVal[1]];
            }
        }
        let selected = cleanedVal.filter((d) => d.selected);
        if (!selected.length && cleanedVal.length) {
            cleanedVal[0].selected = true;
        }
        selected = cleanedVal.filter((d) => d.selected);
        if (selected.length === 1 && cleanedVal.length > 1) {
            cleanedVal.find((d) => !d.selected).selected = true;
        }
        this._value.images = cleanedVal;
        selected = cleanedVal.filter((d) => d.selected);
        this.setSelected(selected);
    }

    get value() {
        return this._value;
    }

    setSelected(selected) {
        this._value.images.forEach((d) => (d.selected = false));
        this.node.imgs.length = 0;
        for (const sel of selected) {
            if (!sel.img) {
                sel.img = new Image();
                sel.img.src = sel.url;
                this.node.imgs.push(sel.img);
            }
            sel.selected = true;
        }
        this.selected = selected;
    }

    clickWasWithinBounds(pos, bounds) {
        let xStart = bounds[0];
        let xEnd = xStart + (bounds.length > 2 ? bounds[2] : bounds[1]);
        const clickedX = pos[0] >= xStart && pos[0] <= xEnd;
        if (bounds.length === 2) {
            return clickedX;
        }
        return clickedX && pos[1] >= bounds[1] && pos[1] <= bounds[1] + bounds[3];
    }

    mouse(event, pos, node) {
        const canvas = app.canvas;
        if (event.type == "pointerdown") {
            this.mouseDowned = [...pos];
            this.isMouseDownedAndOver = true;
            this.downedHitAreasForClick = [];
            
            for (const part of Object.values(this.hitAreas)) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    if (part.onClick) {
                        this.downedHitAreasForClick.push(part);
                    }
                    part.wasMouseClickedAndIsOver = true;
                }
            }
            return true;
        }
        
        if (event.type == "pointerup") {
            if (!this.mouseDowned) return true;
            
            const wasMouseDownedAndOver = this.isMouseDownedAndOver;
            this.mouseDowned = null;
            this.isMouseDownedAndOver = false;
            
            for (const part of Object.values(this.hitAreas)) {
                part.wasMouseClickedAndIsOver = false;
            }
            
            for (const part of this.downedHitAreasForClick) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    part.onClick.call(this, event, pos, node, part);
                }
            }
            this.downedHitAreasForClick = [];
            return true;
        }
        
        if (event.type == "pointermove") {
            this.isMouseDownedAndOver = !!this.mouseDowned;
        }
    }

    draw(ctx, node, width, y) {
        this.hitAreas = {};

        y = this.drawActionButtons(ctx, node, y);

        if (this.value.images.length > 2) {
            ctx.textAlign = "left";
            ctx.textBaseline = "top";
            ctx.font = `14px Arial`;
            const drawData = [];
            const spacing = 5;
            let x = 0;
            for (const img of this.value.images) {
                const width = measureText(ctx, img.name);
                drawData.push({
                    img,
                    text: img.name,
                    x,
                    width: measureText(ctx, img.name),
                });
                x += width + spacing;
            }
            x = (node.size[0] - (x - spacing)) / 2;
            for (const d of drawData) {
                ctx.fillStyle = d.img.selected ? "rgba(180, 180, 180, 1)" : "rgba(180, 180, 180, 0.5)";
                ctx.fillText(d.text, x, y);
                this.hitAreas[d.text] = {
                    bounds: [x, y, d.width, 14],
                    data: d.img,
                    onClick: this.onSelectionDown.bind(this),
                };
                x += d.width + spacing;
            }
            y += 20;
        }
        if (node.properties?.["comparer_mode"] === "Click") {
            this.drawImage(ctx, this.selected[this.node.isPointerDown ? 1 : 0], y);
        }
        else {
            // Slide 모드: 원본과 동일한 방식
            this.drawImage(ctx, this.selected[0], y);
            if (node.isPointerOver) {
                this.drawImage(ctx, this.selected[1], y, this.node.pointerOverPos[0]);
            }
        }
    }

    drawActionButtons(ctx, node, y) {
        const labels = [
            { key: "A", text: "A" },
            { key: "B", text: "B" },
            { key: "retry", text: "Retry" },
            { key: "cancel", text: "Cancel" },
        ];

        const horizontalMargin = 8;
        const spacing = 4;
        const buttonHeight = 20;
        const totalSpacing = spacing * (labels.length - 1);
        const buttonWidth = (node.size[0] - horizontalMargin * 2 - totalSpacing) / labels.length;
        let buttonX = horizontalMargin;

        for (const item of labels) {
            const isPressed = this.downedHitAreasForClick.some((part) => part.key === `select_${item.key}` && part.wasMouseClickedAndIsOver);
            const isWaiting = !!node.isWaiting;
            const alpha = isWaiting ? 1 : 0.45;

            ctx.fillStyle = isPressed
                ? `rgba(95, 145, 95, ${alpha})`
                : `rgba(35, 35, 35, ${alpha})`;
            ctx.strokeStyle = `rgba(100, 100, 100, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(buttonX, y, buttonWidth, buttonHeight, 5);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = `rgba(230, 230, 230, ${alpha})`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.font = "12px Arial";
            ctx.fillText(item.text, buttonX + buttonWidth / 2, y + buttonHeight / 2);

            this.hitAreas[`select_${item.key}`] = {
                key: `select_${item.key}`,
                bounds: [buttonX, y, buttonWidth, buttonHeight],
                data: item.key,
                onClick: this.onActionButtonClick.bind(this),
            };

            buttonX += buttonWidth + spacing;
        }

        return y + buttonHeight + 8;
    }

    async onActionButtonClick(event, pos, node, bounds) {
        if (!node.isWaiting) {
            return;
        }

        const action = bounds?.data;
        if (!action) {
            return;
        }

        const result = await sendComparerMessage(node.id, action);
        if (result?.code === 1) {
            node.isWaiting = false;
            node.setDirtyCanvas(true, true);
        }
    }

    onSelectionDown(event, pos, node, bounds) {
        const selected = [...this.selected];
        if (bounds?.data.name.startsWith("A")) {
            selected[0] = bounds.data;
        }
        else if (bounds?.data.name.startsWith("B")) {
            selected[1] = bounds.data;
        }
        this.setSelected(selected);
    }

    drawImage(ctx, image, y, cropX) {
        if (!image?.img?.naturalWidth || !image?.img?.naturalHeight) {
            return;
        }
        let [nodeWidth, nodeHeight] = this.node.size;
        const imageAspect = image?.img.naturalWidth / image?.img.naturalHeight;
        let height = nodeHeight - y;
        const widgetAspect = nodeWidth / height;
        let targetWidth, targetHeight;
        let offsetX = 0;
        if (imageAspect > widgetAspect) {
            targetWidth = nodeWidth;
            targetHeight = nodeWidth / imageAspect;
        }
        else {
            targetHeight = height;
            targetWidth = height * imageAspect;
            offsetX = (nodeWidth - targetWidth) / 2;
        }
        const widthMultiplier = image?.img.naturalWidth / targetWidth;
        const sourceX = 0;
        const sourceY = 0;
        const sourceWidth = cropX != null ? (cropX - offsetX) * widthMultiplier : image?.img.naturalWidth;
        const sourceHeight = image?.img.naturalHeight;
        const destX = (nodeWidth - targetWidth) / 2;
        const destY = y + (height - targetHeight) / 2;
        const destWidth = cropX != null ? cropX - offsetX : targetWidth;
        const destHeight = targetHeight;
        ctx.save();
        ctx.beginPath();
        let globalCompositeOperation = ctx.globalCompositeOperation;
        if (cropX) {
            ctx.rect(destX, destY, destWidth, destHeight);
            ctx.clip();
        }
        ctx.drawImage(image?.img, sourceX, sourceY, sourceWidth, sourceHeight, destX, destY, destWidth, destHeight);
        if (cropX != null && cropX >= (nodeWidth - targetWidth) / 2 && cropX <= targetWidth + offsetX) {
            ctx.beginPath();
            ctx.moveTo(cropX, destY);
            ctx.lineTo(cropX, destY + destHeight);
            ctx.globalCompositeOperation = "difference";
            ctx.strokeStyle = "rgba(255,255,255, 1)";
            ctx.stroke();
        }
        ctx.globalCompositeOperation = globalCompositeOperation;
        ctx.restore();
    }

    computeSize(width) {
        return [width, 20];
    }

    serializeValue(node, index) {
        const v = [];
        for (const data of this._value.images) {
            const d = { ...data };
            delete d.img;
            v.push(d);
        }
        return { images: v };
    }
}
