import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function imageDataToUrl(data) {
    return api.apiURL(`/view?filename=${encodeURIComponent(data.filename)}&type=${data.type}&subfolder=${data.subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`);
}

function measureText(ctx, text) {
    return ctx.measureText(text).width;
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
            const origOnExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(output) {
                // 먼저 canvasWidget 초기화 확인
                if (!this.canvasWidget) return;
                
                if ("images" in output) {
                    this.canvasWidget.value = {
                        images: (output.images || []).map((d, i) => {
                            return {
                                name: i === 0 ? "A" : "B",
                                selected: true,
                                url: imageDataToUrl(d),
                            };
                        }),
                    };
                }
                else {
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
                    this.canvasWidget.value = { images: imagesToChoose };
                }
                
                // ComfyUI의 기본 이미지 배열을 비워서 기본 UI가 표시되지 않도록 함
                // (이미지는 커스텀 위젯에서 관리)
                this.imgs = [];
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
