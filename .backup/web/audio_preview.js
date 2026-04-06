import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// 오디오 프리뷰 메시지 전송
async function sendAudioPreviewMessage(nodeId, action) {
    try {
        const response = await api.fetchApi("/ghtools/audio_preview_message", {
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
        console.error("Audio preview message failed:", error);
        return { code: -1, error: error.message };
    }
}

// 직렬화 비활성화
function disableSerialize(widget) {
    if (!widget.options) widget.options = {};
    widget.options.serialize = false;
}

// base64를 Blob으로 변환
function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

app.registerExtension({
    name: 'ghtools.audioPreview',
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === 'GHAudioPreview') {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // 상태 추적
                this.isWaiting = false;
                this._audioElement = null;
                this._audioUrl = null;
                
                const self = this;
                
                // 재생/정지 버튼
                this.playButton = this.addWidget("button", "Play", null, function() {
                    if (self._audioElement) {
                        if (self._audioElement.paused) {
                            self._audioElement.play();
                        } else {
                            self._audioElement.pause();
                        }
                    }
                });
                disableSerialize(this.playButton);
                
                // Accept 버튼
                this.acceptButton = this.addWidget("button", "Accept", null, function() {
                    if (self.isWaiting) {
                        sendAudioPreviewMessage(self.id, "accept");
                        self.isWaiting = false;
                        self.updateButtons();
                    }
                });
                disableSerialize(this.acceptButton);
                
                // Retry 버튼
                this.retryButton = this.addWidget("button", "Retry", null, function() {
                    if (self.isWaiting) {
                        sendAudioPreviewMessage(self.id, "retry");
                        self.isWaiting = false;
                        self.cleanupAudio();
                        self.updateButtons();
                    }
                });
                disableSerialize(this.retryButton);
                
                // Cancel 버튼
                this.cancelButton = this.addWidget("button", "Cancel", null, function() {
                    if (self.isWaiting) {
                        sendAudioPreviewMessage(self.id, "cancel");
                        self.isWaiting = false;
                        self.cleanupAudio();
                        self.updateButtons();
                    }
                });
                disableSerialize(this.cancelButton);
                
                // 오디오 정리 함수
                this.cleanupAudio = function() {
                    if (this._audioElement) {
                        this._audioElement.pause();
                        this._audioElement = null;
                    }
                    if (this._audioUrl) {
                        URL.revokeObjectURL(this._audioUrl);
                        this._audioUrl = null;
                    }
                };
                
                // 버튼 상태 업데이트 함수
                this.updateButtons = function() {
                    if (this.isWaiting) {
                        this.playButton.name = this._audioElement && !this._audioElement.paused ? "⏸ Pause" : "▶ Play";
                        this.acceptButton.name = "✔ Accept";
                        this.retryButton.name = "↻ Retry";
                        this.cancelButton.name = "✖ Cancel";
                        this.bgcolor = "#335533";
                    } else {
                        this.playButton.name = this._audioElement && !this._audioElement.paused ? "⏸ Pause" : (this._audioElement ? "▶ Play" : "Play");
                        this.acceptButton.name = "Accept";
                        this.retryButton.name = "Retry";
                        this.cancelButton.name = "Cancel";
                        this.bgcolor = null;
                    }
                    this.setDirtyCanvas(true, true);
                };
                
                // 오디오 설정 함수
                this.setAudio = function(audioData, sampleRate) {
                    this.cleanupAudio();
                    
                    const audioBlob = base64ToBlob(audioData, 'audio/wav');
                    this._audioUrl = URL.createObjectURL(audioBlob);
                    this._audioElement = new Audio(this._audioUrl);
                    
                    const self = this;
                    this._audioElement.addEventListener('ended', () => {
                        self.playButton.name = "▶ Play";
                        self.setDirtyCanvas(true, true);
                    });
                    
                    this._audioElement.addEventListener('play', () => {
                        self.playButton.name = "⏸ Pause";
                        self.setDirtyCanvas(true, true);
                    });
                    
                    this._audioElement.addEventListener('pause', () => {
                        self.playButton.name = "▶ Play";
                        self.setDirtyCanvas(true, true);
                    });
                };
                
                // 초기 버튼 상태
                this.updateButtons();
                
                return result;
            };
            
            // 노드 제거 시 정리
            const onRemoved = nodeType.prototype.onRemoved;
            nodeType.prototype.onRemoved = function() {
                this.cleanupAudio?.();
                return onRemoved?.apply(this, arguments);
            };
        }
    },
    
    setup(app) {
        // 오디오 프리뷰 대기 상태 이벤트 수신
        api.addEventListener("ghtools-audio-preview-waiting", (event) => {
            const { id, audio_data, sample_rate } = event.detail;
            const node = app.graph._nodes_by_id[id];
            if (node && node.type === 'GHAudioPreview') {
                node.isWaiting = true;
                node.setAudio(audio_data, sample_rate);
                node.updateButtons();
            }
        });
        
        // Retry 시 자동 재큐잉
        api.addEventListener("ghtools-audio-preview-retry", (event) => {
            const { id } = event.detail;
            console.log("[AudioPreview] Retry requested, re-queueing prompt...");
            
            // 약간의 딜레이 후 재큐잉 (인터럽트 처리 완료 대기)
            setTimeout(() => {
                app.queuePrompt(0, 1);
            }, 100);
        });
        
        // Always Pass 모드에서도 오디오 수신 (재생용)
        api.addEventListener("ghtools-audio-preview-passed", (event) => {
            const { id, audio_data, sample_rate } = event.detail;
            const node = app.graph._nodes_by_id[id];
            if (node && node.type === 'GHAudioPreview') {
                node.setAudio(audio_data, sample_rate);
                node.updateButtons?.();
            }
        });
        
        // 실행 시작 시 상태 초기화 (오디오는 유지 — 새 오디오 도착 시 교체됨)
        api.addEventListener("execution_start", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHAudioPreview') {
                    node.isWaiting = false;
                    node.updateButtons?.();
                }
            });
        });
        
        // 실행 완료/오류 시 상태 초기화 (오디오는 유지)
        api.addEventListener("execution_cached", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHAudioPreview') {
                    node.isWaiting = false;
                    node.updateButtons?.();
                }
            });
        });
        
        api.addEventListener("execution_error", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHAudioPreview') {
                    node.isWaiting = false;
                    node.updateButtons?.();
                }
            });
        });

        api.addEventListener("execution_interrupted", () => {
            app.graph._nodes.forEach((node) => {
                if (node.type === 'GHAudioPreview') {
                    node.isWaiting = false;
                    node.updateButtons?.();
                }
            });
        });
    }
});
