# Robocup2021用ツール

## 撮影される動画が満たすべき仕様
### must
- 音声を入れる
- ファイルのどこかに撮影開始(≠タスク開始)のdatetime情報を含める
  - 最優先でファイル名から検出する
  - 次に`.mp4`のMetadataを見に行く(AG-Webカメラレコーダーは`.avi`にはdatetimeのMetadataを挿入しないっぽい?)
  - 最終手段として`/video_merger/config/manual_start_times.json`を見に行く

### should
- 音声は48kHz
  - 44.1kHzだと音声検出精度が微妙に下がる
- 動画は30fps
  - それ以外も勝手に調整してくれると思うが動作未確認
- アスペクト比は16:9，特に1280x720が望ましい
  - これ以外を入力しても，ふちが黒くなるだけで済む(多分)
- 動画形式は`.mp4`
- 全てのPCの時刻を同期する

### can
- AG-Webカメラレコーダーなら，デバイス->調整で明るさとかを調整可能

---

## 撮影者
1. スタートメニューなどからAG-Webカメラレコーダーを開く
1. デバイスを選び，**ビデオ形式を`1280x720 30fps`にする**
   - この設定はアプリ起動の度に初期化されてしまう
   - 設定がわからなくなったらエクスプローラ->クイックアクセス->robocup2021
1. 録画する


## operator
1. セットアップをする(順不同)
   -  ロボットの準備を完了させる
   -  SimpleScreenRecorderを起動しておき，`Ctrl`+`Shift`+`R`でデスクトップの起動を開始する
   -  他の全アングルからの撮影開始を待つ
   -  description表示用のPCで`descriptionizer`を開き，今からやる内容を打ち込む
1. **description表示用のPCでタスク開始合図のボタンを押す**
   - (動画結合時にはここで鳴る音で時刻が同期される)
1. ロボットでタスクを行う
1. `Ctrl`+`Shift`+`R`で録画終了する










