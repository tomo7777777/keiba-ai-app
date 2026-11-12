# 競馬AIラボ

中央競馬（JRA）のAI予想アプリです。GitHub Actions で毎日自動更新し、GitHub Pages でスマホから見られます。

- 全レースのAI勝率・3着内率・期待値（AI勝率×単勝オッズ）と印（◎○▲△）
- 勝負レース：本命（◎の勝率30%以上）と 狙い（期待値1.3以上の穴馬）
- 成績：公開後の実績と、過去データでの検証結果

## 仕組み

| ファイル | 役割 |
|---|---|
| `scripts/netkeiba.py` | 出馬表・オッズ・結果の取得 |
| `scripts/features.py` | 過去成績から特徴量を作成（レース前に分かる情報のみ） |
| `scripts/train.py` | LightGBM で勝率・3着内率を学習 |
| `scripts/backtest.py` | 学習に使っていない期間で買い方を検証 |
| `scripts/strategy.py` | 印と買い目のルール |
| `scripts/predict.py` | 当日の予想（朝に固定・オッズは随時更新） |
| `scripts/results.py` | 結果の取得と成績集計 |
| `.github/workflows/update.yml` | 毎日 6:40〜17:40 に20分ごと実行（開催日のみ動作） |
| `.github/workflows/weekly.yml` | 毎週火曜に結果を取り込み学習し直し |
| `docs/` | スマホ用の画面（GitHub Pages） |

予想は参考情報です。馬券の購入はご自身の判断でお願いします。
