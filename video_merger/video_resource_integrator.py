import os
import glob
import json
import re
import shutil

input_parent_dirname = os.path.join(os.path.dirname(__file__), "input", "shinobi_res")
output_dirname = os.path.join(os.path.dirname(__file__), "input")
ignored_log_fullname = os.path.join(os.path.dirname(__file__), "log", "ignored_by_integrator.json")
input_pc_names = ["pc1", "pc2", "pc3"]
rename_dirname = os.path.join(os.path.dirname(__file__), "input", "shinobi_res", "other-videos")


def integrate():
    ignored = {}
    for input_pc_name in input_pc_names:
        input_fullnames = glob.glob(os.path.join(input_parent_dirname, input_pc_name, "*"))
        for input_fullname in input_fullnames:
            input_basename = os.path.basename(input_fullname)
            output_basename = None

            # リネームの必要が無ければそのままコピーする
            if re.fullmatch(r"pc\d_\d{8}_\d{6}.(avi|mp4|mkv|wmv|mov)", input_basename) is not None:
                output_basename = input_basename

            # Windows標準のカメラアプリのファイルをリネームする
            if re.fullmatch(r"WIN_\d{8}_\d{2}_\d{2}_\d{2}_Pro.(avi|mp4|mkv|wmv|mov)", input_basename) is not None:
                date = input_basename[4:12]
                hour = input_basename[13:15]
                minute = input_basename[16:18]
                second = input_basename[19:21]
                extension = input_basename[26:]
                output_basename = f"{input_pc_name}_{date}_{hour}{minute}{second}.{extension}"

            # copy2はメタデータもコピーするはず
            if output_basename is None:
                ignored[input_pc_name] = input_basename
                continue
            output_fullname = os.path.join(output_dirname, output_basename)
            if not os.path.exists(output_fullname):
                shutil.copy2(input_fullname, output_fullname)

            print(f"{input_basename} is integrated")

        with open(ignored_log_fullname, "w") as f:
            json.dump(ignored, f, indent=4)


def rename():
    input_fullnames = glob.glob(os.path.join(rename_dirname, "*"))
    for input_fullname in input_fullnames:
        input_basename = os.path.basename(input_fullname)
        output_basename = None

        # Windows標準のカメラアプリのファイルをリネームする
        if re.fullmatch(r"WIN_\d{8}_\d{2}_\d{2}_\d{2}_Pro\.(avi|mp4|mkv|wmv|mov)", input_basename) is not None:
            date = input_basename[4:12]
            hour = input_basename[13:15]
            minute = input_basename[16:18]
            second = input_basename[19:21]
            extension = input_basename[26:]
            output_basename = f"pc1_{date}_{hour}{minute}{second}.{extension}"

        # Xperia Z5 Compactのファイルをリネームする
        if re.fullmatch(r"VID_\d{8}_\d{2}\d{2}\d{2}\.(avi|mp4|mkv|wmv|mov)", input_basename) is not None:
            date = input_basename[4:12]
            hour = input_basename[13:15]
            minute = input_basename[15:17]
            second = input_basename[17:19]
            extension = input_basename[20:]
            output_basename = f"pc1_{date}_{hour}{minute}{second}.{extension}"

        # 何かの判定条件に引っ掛かっていたらリネームする
        if output_basename is not None:
            output_fullname = os.path.join(rename_dirname, output_basename)
            os.rename(input_fullname, output_fullname)


if __name__ == "__main__":
    integrate()
    # rename()
