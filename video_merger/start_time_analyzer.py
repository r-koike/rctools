import os
import glob
import json
import numpy as np
import matplotlib.pyplot as plt  # noqa

import wave
import ffmpeg
from scipy import signal

# Hz単位で，これ以降の周波数判定に使う周波数範囲，及び目的音声の周波数を指定する
# 700Hzよりも低周波数の場所は人の声などでnoisyなので非推奨
# [target_frequency]の整数倍の値は範囲に含めないべき
lower_limit_frequency = 700
upper_limit_frequency = 1900
target_frequency = 1000

# 目的周波数の音がこれよりも長い場合に，それは目的音声であると判断する(秒単位)
target_min_timelength = 0.4

input_dirname = os.path.join(os.path.dirname(__file__), "input")
audio_dirname = os.path.join(os.path.dirname(__file__), "temp", "audio")
output_fullname = os.path.join(os.path.dirname(__file__), "config", "analyzed_start_times.json")
extract_log_fullname = os.path.join(os.path.dirname(__file__), "log", "error_in_st_analyzer.json")

error_in_extracting = {}

results = {}
with open(output_fullname) as f:
    results = json.load(f)


def extract_audios():
    input_video_fullnames = glob.glob(os.path.join(input_dirname, "*"))
    for input_video_fullname in input_video_fullnames:
        if not os.path.isfile(input_video_fullname):
            continue

        # 例えば[1000Hz_test.mp4.wav]のような二重拡張子がついた名前になるが，誤植ではない
        audio_basename = os.path.basename(input_video_fullname)+".wav"
        audio_fullname = os.path.join(audio_dirname, audio_basename)
        if not os.path.exists(audio_fullname):
            try:
                ffmpeg.input(input_video_fullname).output(audio_fullname, format="wav").run()
            except ffmpeg._run.Error:
                error_in_extracting[audio_basename] = "extracting video->wav error"
                results[os.path.basename(input_video_fullname)] = []

    with open(extract_log_fullname, "w") as f:
        json.dump(error_in_extracting, f, indent=4)


def analyze():
    audio_fullnames = glob.glob(os.path.join(audio_dirname, "*"))
    for audio_fullname in audio_fullnames:
        audio_basename = os.path.basename(audio_fullname)
        video_basename = os.path.splitext(audio_basename)[0]
        # 既に解析済みだったら無視する
        if video_basename in results:
            continue

        wave_file = wave.open(audio_fullname, "r")

        # [num_frames]はオーディオの時間軸方向にいくつのフレームがあるかを表す
        # [frame_rate]はサンプリング周波数のことで，だいたい48000か44100になりがち
        num_frames = wave_file.getnframes()
        frame_rate = wave_file.getframerate()
        # print(num_frames, frame_rate)

        # binaryからnpに変換するとき，音声形式によってはint32よりもint16の方が適切な場合もある
        # ゴリ押し実装だが，32ビット整数でダメなら2つとも試してみる
        # TODO: binaryのサイズを読んだりしてちゃんと実装する
        y_binary = wave_file.readframes(num_frames)
        y = np.frombuffer(y_binary, dtype="int32")
        if y.shape[0] != num_frames:
            y = np.frombuffer(y_binary, dtype="int16")
        _ = np.arange(0, len(y)) / float(frame_rate)
        assert y.shape[0] == num_frames

        wave_file.close()

        # セグメント長さやオーバーラップは以下リンクがわかりやすい
        # https://jp.mathworks.com/help/signal/ug/spectrogram-computation-in-signal-analyzer.html
        n_per_segment = 1024
        n_fft = frame_rate / 10
        slide_time_step = 100
        frequencies, times, Sxx = signal.spectrogram(
            y,
            fs=frame_rate,
            window='hanning',
            nperseg=n_per_segment,
            noverlap=n_per_segment - slide_time_step,
            nfft=n_fft,
            detrend=False,
            # scaling='spectrum'
        )
        spectrogram = np.log10(Sxx)
        # print(frequencies.shape)
        # print(times.shape)
        # print(spectrogram.shape)

        # # スペクトルを表示したいとき用
        # _, ax = plt.subplots()
        # ax.pcolormesh(times, frequencies/1000, spectrogram, cmap='viridis')
        # ax.set_ylabel('Frequency[kHz]')
        # ax.set_xlabel('Time[s]')
        # plt.show()

        # plt.plot(frequencies, spectrogram[:, 5040])
        # plt.show()

        # * ---------------------------------------------------------------------------
        # ノイズ除去とかをして所望の音がなっている時刻を計算する

        frequency_stepsize = frame_rate / n_fft
        lower_limit_frequency_i = round(lower_limit_frequency / frequency_stepsize)
        upper_limit_frequency_i = round(upper_limit_frequency / frequency_stepsize)
        target_frequency_i = round(target_frequency / frequency_stepsize)
        # print(lower_limit_frequency_i, upper_limit_frequency_i, target_frequency_i)

        # 周波数方向の下限と上限を使い，スペクトルをカットする
        # [target_frequency_i]もそれに合わせて変更する
        cutted = spectrogram[lower_limit_frequency_i:upper_limit_frequency_i, :]
        target_frequency_i -= lower_limit_frequency_i

        maximum_args = np.argmax(cutted, axis=0)
        detecting_target_rawdata = maximum_args == target_frequency_i

        # [detecting_target_rawdata]のノイズを除去する
        detecting_target_float = detecting_target_rawdata * 1.0
        # 移動平均のサイズ
        convolve_size = 7
        mask = np.ones(convolve_size) / convolve_size
        detecting_target_convolved = np.convolve(detecting_target_float, mask, mode="same")
        detecting_target_saltpepper = detecting_target_convolved > 0.5

        # これでもゴマ塩ノイズが残るので，特定の長さ以上に渡って連続する音声だけを残す
        time_stepsize = slide_time_step / frame_rate
        target_min_step = round(target_min_timelength / time_stepsize)
        # ここはnumpy内で実装するのが面倒だったのでfor文でまわす
        pre_state = detecting_target_saltpepper[0]
        streaks = [0]
        for i in range(len(detecting_target_saltpepper)):
            if pre_state == detecting_target_saltpepper[i]:
                streaks[-1] += 1
            else:
                streaks.append(1)
            pre_state = detecting_target_saltpepper[i]
        current_state = detecting_target_saltpepper[0]
        detecting_target_list = []
        for i in range(len(streaks)):
            inserting_state = False
            if current_state and streaks[i] > target_min_step:
                inserting_state = True
            detecting_target_list.extend([inserting_state] * streaks[i])
            current_state = not current_state
        detecting_target = np.array(detecting_target_list)

        # 山の開始位置を全て検知し，音声ファイルの経過時間に対応させる
        # ここもfor文でやる
        pre_state = detecting_target[0]
        detected_frames = []
        for i in range(len(detecting_target)):
            if pre_state != detecting_target[i] and detecting_target[i]:
                detected_frames.append(i)
            pre_state = detecting_target_saltpepper[i]
        detected_times = times[detected_frames]

        # * ---------------------------------------------------------------------------
        # dictに保存する
        results[video_basename] = detected_times.tolist()

        # print(detected_frames)
        print(f"{video_basename}: {detected_times}")

        # plt.plot(times, detecting_target)
        # plt.show()

    # * ---------------------------------------------------------------------------
    # jsonに保存する
    with open(output_fullname, "w") as f:
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    extract_audios()
    analyze()
