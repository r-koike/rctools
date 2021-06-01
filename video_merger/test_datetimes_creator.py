import os
import glob
import datetime
import json


input_dirname = os.path.join(os.path.dirname(__file__), "config", "description_dump")
output_fullname = os.path.join(os.path.dirname(__file__), "config", "created_test_datetimes.json")
ignored_log_fullname = os.path.join(os.path.dirname(__file__), "log", "ignored_by_td_creator.json")


def create_test_datetimes():
    results = {}
    ignored = {}
    input_fullnames = glob.glob(os.path.join(input_dirname, "*"))
    for input_fullname in input_fullnames:
        input_basename = os.path.basename(input_fullname)

        # "success"と書いていないファイルは無視する
        adopt_this_file = False
        with open(input_fullname) as f:
            for line in f:
                line = line.rstrip()
                if len(line) >= 7 and line[0:7] == "success":
                    adopt_this_file = True
                break
        if not adopt_this_file:
            ignored[input_basename] = "ignored"
            continue

        input_basename_list = input_basename.split("-")

        date_time = datetime.datetime.strptime(input_basename_list[0], "%Y%m%d%H%M%S")
        date_time_string = date_time.strftime("%Y-%m-%d %H:%M:%S")
        output_basename = "-".join(input_basename_list[1:])

        results[date_time_string] = output_basename[:-4]

    with open(output_fullname, "w") as f:
        json.dump(results, f, indent=4)
    with open(ignored_log_fullname, "w") as f:
        json.dump(ignored, f, indent=4)


if __name__ == "__main__":
    create_test_datetimes()
