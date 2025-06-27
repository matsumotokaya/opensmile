#!/usr/bin/env python3
"""
テスト用のサンプル音声ファイルを生成するスクリプト
"""

import numpy as np
import wave
import os

def generate_sine_wave(frequency, duration, sample_rate=16000, amplitude=0.5):
    """
    正弦波を生成
    
    Args:
        frequency (float): 周波数 (Hz)
        duration (float): 時間 (秒)
        sample_rate (int): サンプリングレート
        amplitude (float): 振幅 (0.0-1.0)
    
    Returns:
        numpy.ndarray: 音声データ
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
    return (wave_data * 32767).astype(np.int16)

def generate_chirp(start_freq, end_freq, duration, sample_rate=16000, amplitude=0.5):
    """
    チャープ信号（周波数が時間とともに変化）を生成
    
    Args:
        start_freq (float): 開始周波数 (Hz)
        end_freq (float): 終了周波数 (Hz)
        duration (float): 時間 (秒)
        sample_rate (int): サンプリングレート
        amplitude (float): 振幅 (0.0-1.0)
    
    Returns:
        numpy.ndarray: 音声データ
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # 線形チャープ
    freq_array = start_freq + (end_freq - start_freq) * t / duration
    phase = 2 * np.pi * np.cumsum(freq_array) / sample_rate
    wave_data = amplitude * np.sin(phase)
    return (wave_data * 32767).astype(np.int16)

def save_wav_file(audio_data, filename, sample_rate=16000):
    """
    音声データをWAVファイルとして保存
    
    Args:
        audio_data (numpy.ndarray): 音声データ
        filename (str): ファイル名
        sample_rate (int): サンプリングレート
    """
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"音声ファイルを生成しました: {filename}")

def main():
    """メイン関数"""
    print("テスト用サンプル音声ファイルを生成中...")
    
    # サンプリングレート
    sample_rate = 16000
    
    # 1. 440Hz正弦波（ラの音）- 3秒
    sine_wave = generate_sine_wave(440, 3.0, sample_rate)
    save_wav_file(sine_wave, "sample_sine_440hz.wav", sample_rate)
    
    # 2. 880Hz正弦波（高いラの音）- 2秒
    sine_wave_high = generate_sine_wave(880, 2.0, sample_rate)
    save_wav_file(sine_wave_high, "sample_sine_880hz.wav", sample_rate)
    
    # 3. チャープ信号（200Hz〜2000Hz）- 4秒
    chirp_wave = generate_chirp(200, 2000, 4.0, sample_rate)
    save_wav_file(chirp_wave, "sample_chirp.wav", sample_rate)
    
    # 4. 低周波数正弦波（100Hz）- 2秒
    sine_wave_low = generate_sine_wave(100, 2.0, sample_rate)
    save_wav_file(sine_wave_low, "sample_sine_100hz.wav", sample_rate)
    
    # 5. 複合音（440Hz + 880Hz）- 3秒
    sine1 = generate_sine_wave(440, 3.0, sample_rate, 0.3)
    sine2 = generate_sine_wave(880, 3.0, sample_rate, 0.3)
    composite_wave = sine1 + sine2
    save_wav_file(composite_wave, "sample_composite.wav", sample_rate)
    
    print("\n生成されたファイル:")
    wav_files = [f for f in os.listdir('.') if f.endswith('.wav')]
    for i, file in enumerate(wav_files, 1):
        print(f"  {i}. {file}")
    
    print(f"\n合計 {len(wav_files)} 個のWAVファイルが生成されました。")

if __name__ == "__main__":
    main()