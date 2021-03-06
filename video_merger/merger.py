import os
import json
import datetime
import glob
import re

import ffmpeg
import enum


class OverrideConfig(enum.Enum):
    # each: 各ファイルで選択する(その都度プログラムが止まる)
    # series: (1),(2),...という名前付けで処理される
    override = enum.auto()
    series = enum.auto()
    each = enum.auto()
    ignore = enum.auto()


OUTPUT_FPS = 30
BASE_DATETIME = datetime.datetime(2021, 1, 1, hour=0, minute=0, second=0)

# 開始時刻がこの秒数以上[test_datetimes.json]の設定とズレている動画はignoreする
SAME_TEST_MERGIN = 15.0

OVERRIDE_OUTPUT_VIDEO = OverrideConfig.series


video_dirname = os.path.join(os.path.dirname(__file__), "input")
output_dirname = os.path.join(os.path.dirname(__file__), "output")
analyzed_start_times_fullname = os.path.join(os.path.dirname(__file__), "config", "analyzed_start_times.json")
manual_start_times_fullname = os.path.join(os.path.dirname(__file__), "config", "manual_start_times.json")
test_datetimes_fullname = os.path.join(os.path.dirname(__file__), "config", "created_test_datetimes.json")
manual_test_datetimes_fullname = os.path.join(os.path.dirname(__file__), "config", "manual_test_datetimes.json")
manual_config_fullname = os.path.join(os.path.dirname(__file__), "config", "manual_config.json")
ignored_log_fullname = os.path.join(os.path.dirname(__file__), "log", "ignored_by_merger.json")

video_packet_list = []
video_start_times = {}
ignored_videos = {}


# [左上，右上，左下，右下]になるようにここで調節する
# 今のところ，[pc1, pc2, pc3, operation]の組み合わせを想定していて，
# 問答無用で[pc1, operation, pc2, pc3]の順に並べる
# TODO: ここはconfigファイルとかを読むようにする
def sort_video_basenames(v0, v1, v2, v3):
    raw_list = [v0, v1, v2, v3]
    sorted_list = sorted(raw_list)
    return [sorted_list[1], sorted_list[0], sorted_list[2], sorted_list[3]]


def fetch_start_datetime_delta(video_fullname, start_time):
    video_basename = os.path.basename(video_fullname)

    if re.fullmatch(
            r"pc\d_\d{8}_\d{6}.(avi|mp4|mkv|wmv|mov)",
            video_basename
    ) is not None:
        video_start_datetime_string = video_basename[4:19]
        video_start_datetime = datetime.datetime.strptime(video_start_datetime_string, "%Y%m%d_%H%M%S")
        start_datetime_delta = (video_start_datetime - BASE_DATETIME).total_seconds() + start_time
        return start_datetime_delta

    if re.fullmatch(
        r"operation-pc-\d{4}-\d{2}-\d{2}_\d{2}.\d{2}.\d{2}.(avi|mp4|mkv|wmv|mov)",
        video_basename
    ) is not None:
        video_start_datetime_string = video_basename[13:32]
        video_start_datetime = datetime.datetime.strptime(video_start_datetime_string, "%Y-%m-%d_%H.%M.%S")
        start_datetime_delta = (video_start_datetime - BASE_DATETIME).total_seconds() + start_time
        return start_datetime_delta

    # mp4ファイルの情報として作成日時を記録していないかチェックする
    video_info = ffmpeg.probe(video_fullname)
    try:
        video_info_datetime_string = video_info["format"]["tags"]["creation_time"]
    except KeyError:
        pass
    else:
        s = video_info_datetime_string[:19]
        video_start_datetime = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        start_datetime_delta = (video_start_datetime - BASE_DATETIME).total_seconds() + start_time
        return start_datetime_delta

    return None


def make_dicts():
    global video_start_times, ignored_videos, video_packet_list

    with open(analyzed_start_times_fullname) as f:
        video_start_time_dict = json.load(f)
    with open(manual_start_times_fullname) as f:
        manual_video_start_time_dict = json.load(f)
    with open(test_datetimes_fullname) as f:
        test_datetimes_dict = json.load(f)
    with open(manual_test_datetimes_fullname) as f:
        manual_test_datetimes_dict = json.load(f)

    # analizedなvideo_start_times_dictをmanualなデータで塗りつぶす
    for key, value in manual_video_start_time_dict.items():
        video_start_time_dict[key] = value
    # createdなtest_datetimes_dictをmanualなデータで塗りつぶす
    for key, value in manual_test_datetimes_dict.items():
        test_datetimes_dict[key] = value

    # test_video_listsの要素は，[title, (基準からの経過秒数), [(この時刻に開始されたvideoたち)]]
    test_video_lists = []
    for date_time_string, title in test_datetimes_dict.items():
        date_time = datetime.datetime.strptime(date_time_string, "%Y-%m-%d %H:%M:%S")
        date_time_delta = (date_time - BASE_DATETIME).total_seconds()
        test_video_lists.append([title, date_time_delta, []])

    # test_video_listsを完成させる
    # start_timeが取得できないvideo，開始のdatetimeが取得できないvideo，二か所以上に所属するvideo，はignoreする
    video_fullnames = glob.glob(os.path.join(video_dirname, "*"))
    for video_fullname in video_fullnames:
        video_basename = os.path.basename(video_fullname)

        # start_timeが一意に定まらないならignoreする
        # 一意に定まったならvideo_start_timesに入れておく
        if video_basename not in video_start_time_dict:
            ignored_videos[video_basename] = "START_TIME_KEY_ERROR: "
            continue
        if len(video_start_time_dict[video_basename]) != 1:
            ignored_videos[video_basename] = f"START_TIME_ERROR: start_time: {video_start_time_dict[video_basename]}"
            continue
        start_time = video_start_time_dict[video_basename][0]
        video_start_times[video_basename] = start_time

        # 開始のdatetime(基準からの経過秒数で表現)を計算し，それができないならignoreする
        start_datetime_delta = fetch_start_datetime_delta(video_fullname, start_time)
        if start_datetime_delta is None:
            ignored_videos[video_basename] = "START_DATETIME_ERROR: start_datetime_delta is None"
            continue

        # test_video_listsのどこに入るのか，そのidを全探索する
        # その候補数が1ではなかったらignoreする
        ids = []
        for i in range(len(test_video_lists)):
            test_datetime_delta = test_video_lists[i][1]
            b0 = test_datetime_delta - SAME_TEST_MERGIN < start_datetime_delta
            b1 = start_datetime_delta < test_datetime_delta + SAME_TEST_MERGIN
            if b0 and b1:
                ids.append(i)
        if len(ids) != 1:
            ignored_videos[video_basename] = f"PACKET_INSERTION_ERROR: ids: {ids}"
            continue

        test_video_lists[ids[0]][2].append(video_basename)

    # test_video_listsのうち，video数がちょうど4の物だけをvideo_packet_listに入れる
    for i in range(len(test_video_lists)):
        title, start_time_delta, video_basenames = test_video_lists[i]
        if len(video_basenames) == 4:
            video_basenames = sort_video_basenames(*video_basenames)
            video_packet_list.append([f"{title}.mp4", video_basenames])
        else:
            for video_basename in video_basenames:
                ignored_videos[video_basename] = f"PACKET_SIZE_ERROR: title: {title}, " + \
                    f"delta:{start_time_delta}, len: {len(video_basenames)}"


def merge(output_basename, video0, video1, video2, video3):
    video_basenames = [video0, video1, video2, video3]

    # 設定ファイルがあればそれを読みに行く
    configs = {}
    if os.path.exists(manual_config_fullname):
        with open(manual_config_fullname) as f:
            configs = json.load(f)

    # 動画終了までの時間が最も短いものに合わせる
    min_cutted_duration = 9999999999999999.0
    video_fullnames = []
    start_times = []
    video_shapes = []
    for video_basename in video_basenames:
        video_fullname = os.path.join(video_dirname, video_basename)
        video_info = ffmpeg.probe(video_fullname)
        duration = float(video_info["format"]["duration"])
        video_shapes.append((video_info["streams"][0]["width"], video_info["streams"][0]["height"]))

        start_time = video_start_times[video_basename]
        cutted_duration = duration - start_time
        min_cutted_duration = min(min_cutted_duration, cutted_duration)

        video_fullnames.append(video_fullname)
        start_times.append(start_time)

    original_videos = []
    original_audios = []
    for i in range(len(video_basenames)):
        print(start_times[i], min_cutted_duration)

        stream = ffmpeg.input(video_fullnames[i], ss=start_times[i], t=min_cutted_duration)
        audio = stream.audio
        original_width, original_height = video_shapes[i]

        # width:height = 16:9 になるようにcropする
        # TODO: 別のアスペクト比に対応する
        if original_width * 9 > original_height * 16:
            # 横長の画像
            ow, oh = original_width, original_height
            h = oh
            w = (h * 16) // 9
            x = (ow - w) // 2
            y = 0
            stream = ffmpeg.crop(stream, x, y, w, h)
        elif original_width * 9 < original_height * 16:
            # 縦長の画像
            ow, oh = original_width, original_height
            w = ow
            h = (w * 9) // 16
            x = 0
            y = (oh - h) // 2
            stream = ffmpeg.crop(stream, x, y, w, h)

        video = (
            stream
            .filter("scale", 1280, 720)
            .filter("fps", fps=OUTPUT_FPS)
        )
        original_audios.append(audio)
        original_videos.append(video)

    # コーデックを指定する
    # "libx264"->GPU無くてもOK，"h264_nvenc"->cudaアクセラレーション
    vcodec = "libx264"
    if "vcodec" in configs:
        vcodec = configs["vcodec"]

    # 動画を保存する
    # run()は最後に呼ばれる
    # audioはてきとうに0番目の入力からとっている
    # ? audioの入力はどれをとるのがいいか
    top_video = ffmpeg.filter([original_videos[0], original_videos[1]], "hstack")
    bottom_video = ffmpeg.filter([original_videos[2], original_videos[3]], "hstack")
    merged_video = ffmpeg.filter([top_video, bottom_video], "vstack")
    output_fullname = os.path.join(output_dirname, output_basename)
    _ = (
        ffmpeg
        .output(merged_video, original_audios[0], output_fullname, vcodec=vcodec)
        .run()
    )


def merge_all_videos():
    make_dicts()

    for output_basename, video_basenames in video_packet_list:
        # スペースをアンダーバーに
        output_basename = output_basename.replace(" ", "_")
        output_fullname = os.path.join(output_dirname, output_basename)
        if os.path.exists(output_fullname):
            if OVERRIDE_OUTPUT_VIDEO == OverrideConfig.override:
                os.remove(output_fullname)
            elif OVERRIDE_OUTPUT_VIDEO == OverrideConfig.series:
                basename_without_extension = os.path.splitext(output_basename)[0]
                while os.path.exists(output_fullname):
                    # 今は(100)まで作れる
                    if re.fullmatch(r".+\(\d\)", basename_without_extension) is not None:
                        current_number = int(basename_without_extension[-2])
                        basename_without_extension = f"{basename_without_extension}({current_number+1})"
                    elif re.fullmatch(r".+\(\d{2}\)", basename_without_extension) is not None:
                        current_number = int(basename_without_extension[-3:-1])
                        basename_without_extension = f"{basename_without_extension}({current_number+1})"
                    else:
                        basename_without_extension = basename_without_extension + "(1)"
                    output_basename = basename_without_extension + ".mp4"
                    output_fullname = os.path.join(output_dirname, output_basename)
            elif OVERRIDE_OUTPUT_VIDEO == OverrideConfig.each:
                pass
            elif OVERRIDE_OUTPUT_VIDEO == OverrideConfig.ignore:
                continue

        print("-----------------------------")
        print(output_basename, video_basenames)
        merge(output_basename, *video_basenames)

    with open(ignored_log_fullname, "w") as f:
        json.dump(ignored_videos, f, indent=4)


def merge_one_video():
    output_basename = "Test-Title-6.mp4"
    video_basenames = [
        "pc1_20210531_214633.mp4",
        "pc2_20210531_214630.mp4",
        "pc3_20210531_214632.mp4",
        "operation-pc-2021-05-31_21.46.37.mkv"
    ]

    video_basenames = sort_video_basenames(*video_basenames)
    output_fullname = os.path.join(output_dirname, output_basename)
    if os.path.exists(output_fullname):
        os.remove(output_fullname)
    make_dicts()
    merge(output_basename, *video_basenames)


if __name__ == "__main__":
    merge_all_videos()
    # merge_one_video()
