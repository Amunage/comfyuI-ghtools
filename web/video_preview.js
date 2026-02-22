import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// 비디오 미리보기 액션 전송
async function sendVideoPreviewAction(nodeId, action) {
    try {
        const response = await api.fetchApi("/ghtools/video_preview_action", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                node_id: nodeId,
                action: action
            }),
        });
        return await response.json();
    } catch (error) {
        console.error("Video preview action failed:", error);
        return { code: -1, error: error.message };
    }
}

// 직렬화 비활성화
function disableSerialize(widget) {
    if (!widget.options) widget.options = {};
    widget.options.serialize = false;
}

// 노드 높이 조정
function fitHeight(node) {
    node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]]);
    node?.graph?.setDirtyCanvas(true);
}

// 콜백 체인 함수
function chainCallback(object, property, callback) {
    if (object == undefined) {
        console.error("Tried to add callback to non-existent object");
        return;
    }
    if (property in object && object[property]) {
        const callback_orig = object[property];
        object[property] = function () {
            const r = callback_orig.apply(this, arguments);
            callback.apply(this, arguments);
            return r;
        };
    } else {
        object[property] = callback;
    }
}

// Format widgets 추가 함수 (VHS.core.js의 addFormatWidgets 참조)
function addFormatWidgets(nodeType, nodeData) {
    // nodeData에서 format 정의 가져오기
    const formatDef = nodeData?.input?.required?.format;
    const nodeFormatOptions = (formatDef && formatDef[1]?.formats) || {};
    
    chainCallback(nodeType.prototype, "onNodeCreated", function() {
        const formatWidget = this.widgets?.find(w => w.name === "format");
        if (!formatWidget) {
            return;
        }
        
        // widget.options.formats 또는 nodeData에서 가져온 formats 사용
        const formatOptions = formatWidget.options?.formats || nodeFormatOptions || {};
        let currentWidgets = [];
        
        const self = this;
        // 저장된 동적 위젯 값 (format별로 저장)
        self.formatWidgetValues = self.formatWidgetValues || {};
        
        const updateFormatWidgets = (restoreValues = null) => {
            // 현재 위젯 값 저장 (제거 전)
            if (currentWidgets.length > 0 && self._lastFormat) {
                self.formatWidgetValues[self._lastFormat] = {};
                for (const w of currentWidgets) {
                    self.formatWidgetValues[self._lastFormat][w.name] = w.value;
                }
            }
            
            // 기존 format widgets 제거
            for (const w of currentWidgets) {
                const idx = self.widgets.indexOf(w);
                if (idx > -1) {
                    self.widgets.splice(idx, 1);
                }
            }
            currentWidgets = [];
            
            // 새 format widgets 추가
            const format = formatWidget.value;
            self._lastFormat = format;
            const widgets = formatOptions[format];
            
            // 복원할 값 결정 (restoreValues 우선, 없으면 저장된 값)
            const valuesToRestore = restoreValues || self.formatWidgetValues[format] || {};
            
            if (widgets) {
                const formatIdx = self.widgets.indexOf(formatWidget);
                for (let i = 0; i < widgets.length; i++) {
                    const wDef = widgets[i];
                    const name = wDef[0];
                    const type = wDef[1];
                    const opts = wDef[2] || {};
                    
                    // 복원할 값 또는 기본값
                    const savedValue = valuesToRestore[name];
                    
                    let widget;
                    if (type === "BOOLEAN") {
                        const defaultVal = savedValue !== undefined ? savedValue : (opts.default ?? false);
                        widget = self.addWidget("toggle", name, defaultVal, function(v) {}, { serialize: false });
                    } else if (type === "INT") {
                        const defaultVal = savedValue !== undefined ? savedValue : (opts.default ?? 0);
                        widget = self.addWidget("number", name, defaultVal, function(v) {}, {
                            min: opts.min ?? 0,
                            max: opts.max ?? 100,
                            step: opts.step ?? 1,
                            precision: 0,
                            serialize: false
                        });
                    } else if (type === "FLOAT") {
                        const defaultVal = savedValue !== undefined ? savedValue : (opts.default ?? 0);
                        widget = self.addWidget("number", name, defaultVal, function(v) {}, {
                            min: opts.min ?? 0,
                            max: opts.max ?? 100,
                            step: opts.step ?? 0.1,
                            precision: 2,
                            serialize: false
                        });
                    } else if (type === "STRING") {
                        const defaultVal = savedValue !== undefined ? savedValue : (opts.default ?? "");
                        widget = self.addWidget("text", name, defaultVal, function(v) {}, { serialize: false });
                    } else if (Array.isArray(type)) {
                        // Combo/dropdown
                        const defaultVal = savedValue !== undefined ? savedValue : (opts.default ?? type[0]);
                        widget = self.addWidget("combo", name, defaultVal, function(v) {}, { values: type, serialize: false });
                    }
                    
                    if (widget) {
                        currentWidgets.push(widget);
                        // 위치 조정: format widget 바로 다음에 배치
                        const curIdx = self.widgets.indexOf(widget);
                        if (curIdx > -1) {
                            self.widgets.splice(curIdx, 1);
                            self.widgets.splice(formatIdx + 1 + i, 0, widget);
                        }
                    }
                }
            }
            fitHeight(self);
        };
        
        // format 값 변경 시 widgets 업데이트
        const originalCallback = formatWidget.callback;
        formatWidget.callback = function(value) {
            if (originalCallback) originalCallback.call(this, value);
            updateFormatWidgets();
        };
        
        // 직렬화: 동적 위젯 값 저장
        const origOnSerialize = self.onSerialize;
        self.onSerialize = function(o) {
            if (origOnSerialize) origOnSerialize.call(this, o);
            // 현재 동적 위젯 값을 format별로 저장
            if (currentWidgets.length > 0 && self._lastFormat) {
                self.formatWidgetValues[self._lastFormat] = {};
                for (const w of currentWidgets) {
                    self.formatWidgetValues[self._lastFormat][w.name] = w.value;
                }
            }
            o.formatWidgetValues = self.formatWidgetValues;
            // widgets_values에서 동적 위젯 값을 제거
            // (ComfyUI가 인덱스 기반으로 복원하므로, 동적 위젯 값이 섞이면 밀림 발생)
            if (o.widgets_values && currentWidgets.length > 0) {
                const formatIdx = self.widgets?.indexOf(formatWidget);
                if (formatIdx >= 0) {
                    const fixed = [...o.widgets_values];
                    // 동적 위젯들은 format 바로 다음에 위치
                    fixed.splice(formatIdx + 1, currentWidgets.length);
                    o.widgets_values = fixed;
                }
            }
        };
        
        // 초기화 (onConfigure에서 복원될 수 있도록 지연)
        self._updateFormatWidgets = updateFormatWidgets;
        self._currentFormatWidgets = () => currentWidgets;
        self._formatOptions = formatOptions;
        setTimeout(() => updateFormatWidgets(), 100);

        // configure를 감싸서 widgets_values 인덱스 밀림 방지
        // ComfyUI의 configure()는 widgets_values를 인덱스 기반으로 적용하는데,
        // 저장 시점에 동적 위젯(pix_fmt, crf 등)이 format 뒤에 존재하여
        // widgets_values에 포함되어 있으므로, 로드 시점(동적 위젯 없음)에
        // save_metadata, pingpong 등에 엉뚱한 값이 들어감.
        // → configure 호출 전에 동적 위젯 값을 widgets_values에서 제거.
        const origConfigure = self.configure.bind(self);
        self.configure = function(o) {
            if (o.widgets_values) {
                // format 위젯의 인덱스 찾기 (현재 위젯 배열 기준)
                const fmtIdx = self.widgets?.findIndex(w => w.name === "format");
                if (fmtIdx >= 0) {
                    const format = o.widgets_values[fmtIdx];
                    const dynDefs = formatOptions[format];
                    const dynCount = dynDefs ? dynDefs.length : 0;
                    if (dynCount > 0) {
                        // widgets_values에서 동적 위젯 값을 제거
                        const fixed = [...o.widgets_values];
                        fixed.splice(fmtIdx + 1, dynCount);
                        o.widgets_values = fixed;
                    }
                }
            }
            return origConfigure(o);
        };
    });
    
    // 복원: 저장된 동적 위젯 값 로드
    chainCallback(nodeType.prototype, "onConfigure", function(o) {
        if (o.formatWidgetValues) {
            this.formatWidgetValues = o.formatWidgetValues;
        }
        // 현재 format에 해당하는 동적 위젯 값 복원
        const formatWidget = this.widgets?.find(w => w.name === "format");
        if (formatWidget && this._updateFormatWidgets) {
            const format = formatWidget.value;
            const savedValues = (this.formatWidgetValues && this.formatWidgetValues[format]) || {};
            const self = this;
            setTimeout(() => {
                self._updateFormatWidgets(savedValues);
            }, 150);
        }
    });
}

// 비디오 미리보기 위젯 추가 (VHS.core.js의 addVideoPreview 참조)
function addVideoPreview(nodeType) {
    chainCallback(nodeType.prototype, "onNodeCreated", function() {
        const previewNode = this;
        const element = document.createElement("div");
        
        const previewWidget = this.addDOMWidget("videopreview", "preview", element, {
            serialize: false,
            hideOnZoom: false,
            getValue() {
                return element.value;
            },
            setValue(v) {
                element.value = v;
            },
        });
        
        previewWidget.computeSize = function(width) {
            if (this.aspectRatio && !this.parentEl.hidden) {
                let height = (previewNode.size[0] - 20) / this.aspectRatio + 10;
                if (!(height > 0)) {
                    height = 0;
                }
                this.computedHeight = height + 10;
                return [width, height];
            }
            return [width, -4]; // no loaded src, widget should not display
        };
        
        previewWidget.value = { hidden: false, paused: false, params: {}, muted: true };
        previewWidget.parentEl = document.createElement("div");
        previewWidget.parentEl.className = "ghtools_video_preview";
        previewWidget.parentEl.style['width'] = "100%";
        element.appendChild(previewWidget.parentEl);
        
        // Video element
        previewWidget.videoEl = document.createElement("video");
        previewWidget.videoEl.controls = false;
        previewWidget.videoEl.loop = true;
        previewWidget.videoEl.muted = true;
        previewWidget.videoEl.style['width'] = "100%";
        previewWidget.videoEl.addEventListener("loadedmetadata", () => {
            previewWidget.aspectRatio = previewWidget.videoEl.videoWidth / previewWidget.videoEl.videoHeight;
            fitHeight(previewNode);
        });
        previewWidget.videoEl.addEventListener("error", () => {
            previewWidget.parentEl.hidden = true;
            fitHeight(previewNode);
        });
        previewWidget.videoEl.onmouseenter = () => {
            previewWidget.videoEl.muted = previewWidget.value.muted;
        };
        previewWidget.videoEl.onmouseleave = () => {
            previewWidget.videoEl.muted = true;
        };
        
        // Image element (for gif/webp)
        previewWidget.imgEl = document.createElement("img");
        previewWidget.imgEl.style['width'] = "100%";
        previewWidget.imgEl.hidden = true;
        previewWidget.imgEl.onload = () => {
            previewWidget.aspectRatio = previewWidget.imgEl.naturalWidth / previewWidget.imgEl.naturalHeight;
            fitHeight(previewNode);
        };
        
        previewWidget.parentEl.appendChild(previewWidget.videoEl);
        previewWidget.parentEl.appendChild(previewWidget.imgEl);
        
        // updateParameters 함수
        this.updateParameters = (params, force_update) => {
            if (!previewWidget.value.params) {
                if (typeof(previewWidget.value) != 'object') {
                    previewWidget.value = { hidden: false, paused: false };
                }
                previewWidget.value.params = {};
            }
            Object.assign(previewWidget.value.params, params);
            previewWidget.updateSource();
        };
        
        // updateSource 함수
        previewWidget.updateSource = function() {
            if (this.value.params == undefined) {
                return;
            }
            
            const params = { ...this.value.params };
            params.timestamp = Date.now();
            this.parentEl.hidden = this.value.hidden;
            
            const format = params.format || '';
            const formatType = format.split('/')[0];
            const formatExt = format.split('/')[1];
            
            if (formatType == 'video' || formatExt == 'gif') {
                this.videoEl.autoplay = !this.value.paused && !this.value.hidden;
                this.videoEl.src = api.apiURL('/view?' + new URLSearchParams(params));
                this.videoEl.hidden = false;
                this.imgEl.hidden = true;
            } else if (formatType == 'image') {
                this.imgEl.src = api.apiURL('/view?' + new URLSearchParams(params));
                this.videoEl.hidden = true;
                this.imgEl.hidden = false;
            }
        };
        
        previewWidget.callback = previewWidget.updateSource;
    });
}

app.registerExtension({
    name: 'ghtools.videoPreview',
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === 'GHVideoPreview') {
            // Format widgets 동적 추가
            addFormatWidgets(nodeType, nodeData);
            
            // 비디오 미리보기 위젯 추가
            addVideoPreview(nodeType);
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // 대기 상태 추적
                this.isWaiting = false;
                this.previewInfo = null;
                
                const self = this;
                
                // Save 버튼
                this.saveButton = this.addWidget("button", "💾 Save", null, function() {
                    if (self.isWaiting) {
                        sendVideoPreviewAction(self.id, "save");
                        self.isWaiting = false;
                        self.updateButtons();
                    }
                });
                disableSerialize(this.saveButton);
                
                // Pass 버튼
                this.passButton = this.addWidget("button", "▶ Pass", null, function() {
                    if (self.isWaiting) {
                        sendVideoPreviewAction(self.id, "pass");
                        self.isWaiting = false;
                        self.updateButtons();
                    }
                });
                disableSerialize(this.passButton);
                
                // Retry 버튼
                this.retryButton = this.addWidget("button", "↻ Retry", null, function() {
                    if (self.isWaiting) {
                        sendVideoPreviewAction(self.id, "retry");
                        self.isWaiting = false;
                        self.updateButtons();
                    }
                });
                disableSerialize(this.retryButton);
                
                // Cancel 버튼
                this.cancelButton = this.addWidget("button", "✖ Cancel", null, function() {
                    if (self.isWaiting) {
                        sendVideoPreviewAction(self.id, "cancel");
                        self.isWaiting = false;
                        self.updateButtons();
                    }
                });
                disableSerialize(this.cancelButton);
                
                // 버튼 상태 업데이트 함수
                this.updateButtons = function() {
                    if (this.isWaiting) {
                        this.saveButton.name = "💾 Save Video";
                        this.passButton.name = "▶ Pass Images";
                        this.retryButton.name = "↻ Retry";
                        this.cancelButton.name = "✖ Cancel";
                        // 노드 색상 변경 (대기 상태 표시)
                        this.bgcolor = "#553355";
                    } else {
                        this.saveButton.name = "Save";
                        this.passButton.name = "Pass";
                        this.retryButton.name = "Retry";
                        this.cancelButton.name = "Cancel";
                        // 노드 색상 복원
                        this.bgcolor = null;
                    }
                    this.setDirtyCanvas(true, true);
                };
                
                // 초기 버튼 상태
                this.updateButtons();
                
                return result;
            };
            
            // 미리보기 이미지/비디오 표시를 위한 onExecuted 오버라이드
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(output) {
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
                
                // 미리보기 표시
                if (output && output.gifs && output.gifs.length > 0) {
                    const preview = output.gifs[0];
                    this.previewInfo = preview;
                    
                    // updateParameters 호출하여 미리보기 업데이트
                    if (this.updateParameters) {
                        this.updateParameters(preview);
                    }
                }
            };
        }
    },
    
    setup(app) {
        // 대기 상태 이벤트 수신
        api.addEventListener("ghtools-video-preview-waiting", (event) => {
            const { id, preview } = event.detail;
            const node = app.graph._nodes_by_id[id];
            if (node && node.type === 'GHVideoPreview') {
                node.isWaiting = true;
                node.previewInfo = preview;
                node.updateButtons();
                
                // 미리보기 표시 - updateParameters 사용
                if (preview && node.updateParameters) {
                    node.updateParameters(preview);
                }
            }
        });
        
        // 저장 완료 이벤트
        api.addEventListener("ghtools-video-preview-saved", (event) => {
            const { id, result } = event.detail;
            const node = app.graph._nodes_by_id[id];
            if (node && node.type === 'GHVideoPreview') {
                node.isWaiting = false;
                node.updateButtons();
            }
        });
        
        // Pass 완료 이벤트
        api.addEventListener("ghtools-video-preview-passed", (event) => {
            const { id } = event.detail;
            const node = app.graph._nodes_by_id[id];
            if (node && node.type === 'GHVideoPreview') {
                node.isWaiting = false;
                node.updateButtons();
            }
        });
        
        // Retry 이벤트 - 자동 재큐잉
        api.addEventListener("ghtools-video-preview-retry", (event) => {
            const { id } = event.detail;
            
            // 약간의 딜레이 후 재큐잉 (인터럽트 처리 완료 대기)
            setTimeout(() => {
                app.queuePrompt(0, 1);
            }, 100);
        });
        
        // 실행 시작 시 상태 초기화
        api.addEventListener("execution_start", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHVideoPreview') {
                    node.isWaiting = false;
                    if (node.updateButtons) node.updateButtons();
                }
            });
        });
        
        // 실행 완료/오류 시 상태 초기화
        api.addEventListener("execution_cached", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHVideoPreview') {
                    node.isWaiting = false;
                    if (node.updateButtons) node.updateButtons();
                }
            });
        });
        
        api.addEventListener("execution_error", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHVideoPreview') {
                    node.isWaiting = false;
                    if (node.updateButtons) node.updateButtons();
                }
            });
        });
    }
});
