$root_dir_fullname = Split-Path $MyInvocation.MyCommand.Path
$input_dir_fullname = "${root_dir_fullname}\test"
$output_dir_fullname = "${root_dir_fullname}\output"

$fontsize = 40
$box_height = $fontsize * 2.4

Get-ChildItem "${input_dir_fullname}\*.mp4" -Name | ForEach-Object {
	$input_basename = "${_}"
	$input_fullname = "${input_dir_fullname}\${_}"
	$output_fullname = "${output_dir_fullname}\${_}"

	# 何kgなのか，ファイル名から抽出する
	$input_basename -match "\dkg" | Out-Null
	$actual_weight = $Matches[0]
	$text_content = "'The weight shown on the display in the video is wrong, it is actually 1kg lighter than that, i.e. ${actual_weight}.'"

	ffmpeg -i $input_fullname `
		-vcodec h264_nvenc `
		-filter_complex `
		"drawbox=y=ih-${box_height}:color=white@0.4:width=iw:height=${box_height}:t=fill, `
		drawtext=fontsize=${fontsize}:text=${text_content}:x=w-text_w-5:y=h-text_h-line_h" `
		$output_fullname
}