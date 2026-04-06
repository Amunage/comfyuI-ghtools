"""
Audio Controller Node - 캐릭터 음성 톤 컨트롤러
Praat PSOLA 알고리즘 + 스펙트럴 프로세싱으로 자연스러운 캐릭터 보이스 생성
"""
import importlib
import subprocess
import sys

import numpy as np
import torch


def _ensure_package(package_name, import_name=None):
    """패키지가 없으면 자동 설치 후 import"""
    import_name = import_name or package_name
    try:
        return importlib.import_module(import_name)
    except ImportError:
        pass
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_name],
            stdout=subprocess.DEVNULL,
        )
        return importlib.import_module(import_name)
    except Exception as exc:
        raise RuntimeError(
            f"`{package_name}` 자동 설치 실패. "
            f"직접 `pip install {package_name}` 후 다시 시도해 주세요."
        ) from exc


_scipy = _ensure_package("scipy")
from scipy import signal as scipy_signal

try:
    _ensure_package("praat-parselmouth", "parselmouth")
    import parselmouth
    from parselmouth.praat import call
    PARSELMOUTH_AVAILABLE = True
except Exception:
    PARSELMOUTH_AVAILABLE = False


def pitch_shift_psola(audio_np, sample_rate, semitones, formant_ratio=1.0):
    """
    리샘플링 + PSOLA duration 기반 피치 시프팅
    - 피치 변경: 리샘플링 (깨끗함, 아티팩트 없음)
    - 길이 복원: PSOLA duration manipulation (안정적)
    - 포먼트 보정: formant_ratio로 제어
    """
    # 무음 또는 극단적으로 짧은 오디오 체크
    if len(audio_np) < 64:
        return audio_np
    rms = np.sqrt(np.mean(audio_np ** 2))
    if rms < 1e-8:
        return audio_np

    factor = 2.0 ** (semitones / 12.0)
    sound = parselmouth.Sound(audio_np, sampling_frequency=sample_rate)
    orig_duration = sound.get_total_duration()

    # --- 포먼트 보정 ---
    # 리샘플링은 포먼트도 같이 이동시킴
    # formant_ratio=1.0 → 포먼트 원본 유지 (자연스러운 목소리)
    # formant_ratio>1.0 → 포먼트 추가 이동 (더 밝고 가는 느낌)
    formant_correction = formant_ratio / factor

    if abs(formant_correction - 1.0) > 0.001:
        pre_sound = parselmouth.Sound(
            audio_np,
            sampling_frequency=sample_rate / formant_correction
        )
        sound = call(pre_sound, "Resample", sample_rate, 50)

    # --- 피치 변경 (리샘플링) ---
    # sample rate를 factor배로 설정 → 피치 올라가고 길이 줄어듦
    pitched = parselmouth.Sound(
        sound.values[0],
        sampling_frequency=sample_rate * factor
    )
    pitched = call(pitched, "Resample", sample_rate, 50)

    # --- 길이 복원 (PSOLA duration) ---
    new_duration = pitched.get_total_duration()
    if abs(new_duration - orig_duration) > 0.001:
        stretch_factor = orig_duration / new_duration
        manipulation = call(pitched, "To Manipulation", 0.01, 50, 800)
        duration_tier = call(manipulation, "Extract duration tier")
        # 다중 포인트로 더 정밀한 길이 복원
        total = pitched.get_total_duration()
        n_points = max(2, int(total / 0.5))  # 0.5초마다 한 포인트
        for i in range(n_points):
            t = pitched.xmin + 0.001 + (total - 0.002) * i / max(1, n_points - 1)
            call(duration_tier, "Add point", t, stretch_factor)
        call([manipulation, duration_tier], "Replace duration tier")
        pitched = call(manipulation, "Get resynthesis (overlap-add)")

    return pitched.values[0]


def apply_presence_boost(audio_np, sample_rate, amount):
    """
    프레즌스 부스트: 2-5kHz 대역을 강조하여 애니메 목소리의 밝고 선명한 느낌을 만듦
    amount: 0.0(없음) ~ 1.0(강하게)
    """
    if amount <= 0.001 or sample_rate < 8000:
        return audio_np

    nyquist = sample_rate / 2.0
    # 2kHz ~ 5kHz 밴드패스 (Nyquist 초과 방지)
    low_freq = min(2000.0 / nyquist, 0.95)
    high_freq = min(5000.0 / nyquist, 0.99)

    if low_freq >= high_freq:
        return audio_np

    # 밴드패스 필터로 프레즌스 대역 추출
    b, a = scipy_signal.butter(2, [low_freq, high_freq], btype='band')
    presence = scipy_signal.filtfilt(b, a, audio_np)

    # 원본에 프레즌스 대역을 gain으로 더함 (최대 +6dB)
    gain = amount * 1.0  # 0.0 ~ 1.0 → 0 ~ +6dB 상당
    result = audio_np + presence * gain

    return result


def apply_breathiness(audio_np, sample_rate, amount):
    """
    브레시니스: 가벼운 고주파 노이즈를 음성 엔벨로프에 맞춰 섞어
    에어리한 숨결감을 부여.
    amount: 0.0(없음) ~ 1.0(강하게)
    """
    if amount <= 0.001:
        return audio_np

    # 음성 엔벨로프 추출 (힐베르트 변환)
    analytic = scipy_signal.hilbert(audio_np)
    envelope = np.abs(analytic)

    # 엔벨로프 스무딩 (10ms 윈도우)
    window_size = max(1, int(sample_rate * 0.01))
    kernel = np.ones(window_size) / window_size
    envelope = np.convolve(envelope, kernel, mode='same')

    # 고주파 통과 노이즈 생성 (3kHz 이상)
    noise = np.random.randn(len(audio_np))
    nyquist = sample_rate / 2.0
    cutoff = min(3000.0 / nyquist, 0.95)
    b, a = scipy_signal.butter(2, cutoff, btype='high')
    noise = scipy_signal.filtfilt(b, a, noise)

    # 엔벨로프에 맞춰 노이즈 적용 (무음 구간에는 노이즈 안 들어감)
    breath = noise * envelope * amount * 0.15
    result = audio_np + breath

    return result


def normalize_volume(audio_np, target_rms=None, original_rms=None):
    """
    음량 정규화: 원본 RMS에 맞춰 처리 후 음량을 보정
    """
    if original_rms is None or original_rms < 1e-8:
        return audio_np

    current_rms = np.sqrt(np.mean(audio_np ** 2))
    if current_rms < 1e-8:
        return audio_np

    target = original_rms if target_rms is None else target_rms
    scale = target / current_rms
    result = audio_np * scale

    # 클리핑 방지 (소프트 리미팅)
    peak = np.max(np.abs(result))
    if peak > 0.99:
        result = result * (0.99 / peak)

    return result


class AudioVocalRange:
    """
    음성 톤 컨트롤러 (Praat PSOLA + 스펙트럴 프로세싱)
    - 피치 시프팅: 자연스러운 목소리 톤 변경 (반음 단위)
    - 포먼트 제어: 자연스러움 vs 캐릭터 느낌 조절
    - 프레즌스 부스트: 2-5kHz 강조로 밝고 선명한 톤
    - 브레시니스: 에어리한 숨결감 부여
    - 음량 정규화: 처리 후 음량 자동 보정
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "pitch_semitones": ("FLOAT", {
                    "default": 0.0,
                    "min": -12.0,
                    "max": 12.0,
                    "step": 0.5,
                    "tooltip": "피치 변경 (반음). +4~6: 애니 높은 목소리, -4~6: 낮은 목소리",
                }),
                "formant_ratio": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.5,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "포먼트 비율. 1.0=원본 유지(자연스러움), 1.2+=밝은 느낌, 0.8-=굵은 느낌",
                }),
                "presence": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "프레즌스 부스트(2-5kHz). 높을수록 밝고 선명한 톤",
                }),
                "breathiness": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "브레시니스. 에어리한 숨결감.",
                }),
                "normalize": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "처리 후 원본 음량에 맞춰 자동 정규화",
                }),
                "enabled": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "False로 설정하면 바이패스 (원본 출력)",
                }),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "execute"
    CATEGORY = "🐴GHTools/Utils"

    def execute(self, audio, pitch_semitones, formant_ratio,
                presence, breathiness, normalize, enabled):
        # 바이패스
        if not enabled:
            return (audio,)

        if not PARSELMOUTH_AVAILABLE:
            raise RuntimeError(
                "parselmouth가 설치되어 있지 않습니다.\n"
                "pip install praat-parselmouth 로 설치해주세요."
            )

        waveform = audio["waveform"]        # (batch, channels, samples)
        sample_rate = audio["sample_rate"]

        # 변환 불필요한 경우 바로 반환
        no_pitch = (pitch_semitones == 0.0 and formant_ratio == 1.0)
        no_spectral = (presence <= 0.001 and breathiness <= 0.001)
        if no_pitch and no_spectral:
            return (audio,)

        batch_size, num_channels, num_samples = waveform.shape
        results = []

        for b in range(batch_size):
            channel_results = []
            for ch in range(num_channels):
                y = waveform[b, ch].cpu().numpy().astype(np.float64)

                # 원본 RMS 저장 (음량 정규화용)
                original_rms = np.sqrt(np.mean(y ** 2))

                try:
                    # 1) PSOLA 피치 시프팅 + 포먼트 제어
                    if not no_pitch:
                        y = pitch_shift_psola(y, sample_rate, pitch_semitones, formant_ratio)

                    # 2) 프레즌스 부스트
                    if presence > 0.001:
                        y = apply_presence_boost(y, sample_rate, presence)

                    # 3) 브레시니스
                    if breathiness > 0.001:
                        y = apply_breathiness(y, sample_rate, breathiness)

                    # 4) 음량 정규화
                    if normalize:
                        y = normalize_volume(y, original_rms=original_rms)

                except Exception as e:
                    print(f"[AudioVocalRange] 채널 처리 실패 (batch={b}, ch={ch}): {e}")
                    y = waveform[b, ch].cpu().numpy().astype(np.float64)

                channel_results.append(torch.from_numpy(np.array(y, dtype=np.float32)))

            # 채널 길이 맞추기
            min_len = min(c.shape[0] for c in channel_results)
            channel_results = [c[:min_len] for c in channel_results]
            results.append(torch.stack(channel_results))

        # 배치 길이 맞추기
        min_len = min(r.shape[1] for r in results)
        results = [r[:, :min_len] for r in results]
        new_waveform = torch.stack(results).to(waveform.device)

        return ({"waveform": new_waveform, "sample_rate": sample_rate},)
