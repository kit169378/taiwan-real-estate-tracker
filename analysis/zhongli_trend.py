"""桃園市中壢區量價走勢：data/district_metrics.csv → analysis/figures/zhongli_trend.png

用法：python analysis/zhongli_trend.py [專案資料夾]
- 只用季檔（登記期間約三個月）的資料，排除每旬「本期下載」的短期間，避免量的數字失真
- 預售屋的期間是交易日期，比成屋的登記日期早一個月，圖上和成屋放在同一季
"""
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COUNTY, DISTRICT = "桃園市", "中壢區"
CREDIT_CONTROL = "2024-09-11~2024-12-10"  # 2024-09-20 央行第七波選擇性信用管制後的第一季

INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # 中古屋 / 預售屋


def load(root):
    d = pd.read_csv(root / "data" / "district_metrics.csv", encoding="utf-8-sig", dtype=str)
    d = d[(d["縣市"] == COUNTY) & (d["行政區"] == DISTRICT)].copy()
    start = pd.to_datetime(d["資料期間"].str[:10])
    end = pd.to_datetime(d["資料期間"].str[11:])
    d = d[(end - start).dt.days > 80]  # 只留季檔
    d["指標"] = d["指標名稱"].str.replace(r"\[.*\]", "", regex=True)
    d["數值"] = pd.to_numeric(d["數值"])
    t = d.pivot(index="資料期間", columns="指標", values="數值").sort_index()
    # 季檔登記期間到 3/10、6/10…，以結束月份所在季命名
    end = pd.to_datetime(t.index.str[11:])
    t.index = [f"{e.year % 100}Q{(e.month - 1) // 3 + 1}" for e in end]
    return t


def summarize(t, control_label):
    used = t["中古屋住宅每坪單價中位數(元)"] / 1e4
    pre = t["預售屋住宅每坪單價中位數(元)"] / 1e4
    premium = (pre / used - 1) * 100
    i = t.index.get_loc(control_label)
    peak = t.index[i - 1]
    after = t.index[i + 1: -1]  # 管制後滿一季到上一季，不含最新一季
    print(f"{COUNTY}{DISTRICT}，管制前高點 {peak}，管制後 {after[0]}～{after[-1]}，最新 {t.index[-1]}")
    for name in ("預售屋買賣筆數", "成屋買賣筆數"):
        s = t[name]
        print(f"  {name}：高點 {s[peak]:.0f}，管制後平均 {s[after].mean():.0f}"
              f"（{(s[after].mean() / s[peak] - 1) * 100:+.0f}%），最新 {s.iloc[-1]:.0f}")
    print(f"  中古屋單價中位數（萬/坪）：高點 {used[peak]:.1f}，管制後 {used[after].min():.1f}～{used[after].max():.1f}，最新 {used.iloc[-1]:.1f}")
    print(f"  預售屋單價中位數（萬/坪）：高點 {pre[peak]:.1f}，管制後 {pre[after].min():.1f}～{pre[after].max():.1f}，最新 {pre.iloc[-1]:.1f}")
    print(f"  預售屋溢價（%）：管制前 {premium[:i].min():.0f}～{premium[:i].max():.0f}，管制後 {premium[i:].min():.0f}～{premium[i:].max():.0f}")
    return used, pre


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=INK_2, length=0, labelsize=9)
    ax.set_axisbelow(True)


def label_end(ax, x, y, text, color):
    ax.plot(x, y, "o", ms=6, color=color, mec=SURFACE, mew=1.5, zorder=3)
    ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9, color=INK)


def plot(t, used, pre, control_label, out):
    plt.rcParams["font.family"] = "Microsoft JhengHei"
    x = range(len(t))
    ci = t.index.get_loc(control_label)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True, facecolor=SURFACE,
                                   gridspec_kw={"hspace": 0.35})
    fig.suptitle(f"{COUNTY}{DISTRICT}：預售屋成交量大減，單價沒有跟著跌",
                 x=0.06, ha="left", fontsize=14, fontweight="bold", color=INK)

    for ax in (ax1, ax2):
        style(ax)
        ax.axvline(ci - 0.5, color=INK_2, linewidth=1, linestyle=(0, (3, 3)))
    ax1.text(ci - 0.4, 1.02, "2024/9 第七波信用管制", transform=ax1.get_xaxis_transform(),
             fontsize=9, color=INK_2)

    ax1.set_title("住宅每坪單價中位數（萬元）", loc="left", fontsize=10, color=INK_2)
    for s, c, name in ((pre, ORANGE, "預售屋"), (used, BLUE, "中古屋")):
        ax1.plot(x, s, color=c, linewidth=2)
        label_end(ax1, len(t) - 1, s.iloc[-1], f"{name} {s.iloc[-1]:.1f}", c)
    ax1.set_ylim(0, 60)

    ax2.set_title("買賣筆數（每季）", loc="left", fontsize=10, color=INK_2)
    for col, c, name in (("成屋買賣筆數", BLUE, "成屋"), ("預售屋買賣筆數", ORANGE, "預售屋")):
        s = t[col]
        ax2.plot(x, s, color=c, linewidth=2)
        label_end(ax2, len(t) - 1, s.iloc[-1], f"{name} {s.iloc[-1]:,.0f}", c)
        ax2.annotate(f"{s.iloc[ci - 1]:,.0f}", (ci - 1, s.iloc[ci - 1]), xytext=(0, 7),
                     textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax2.set_ylim(0, 3800)
    ax2.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax2.set_xticks(list(x), t.index)
    ax2.set_xlim(-0.5, len(t) + 1.6)

    fig.text(0.06, 0.015,
             "資料：內政部實價登錄季檔（112S1～115S3，登記截止 2026-09-10），依登記日期分季；預售屋為交易日期，較成屋早一個月。\n"
             "24Q4 橫跨管制上路，為過渡季，管制前後比較採 24Q3 對 25Q1～26Q2。\n"
             "單價扣除車位、排除特殊交易；成屋筆數含土地與非住宅，預售屋筆數含非住宅。",
             fontsize=8, color=INK_2)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.15)
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print(f"  圖表：{out}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    t = load(root)
    end = pd.to_datetime(CREDIT_CONTROL[11:])
    control_label = f"{end.year % 100}Q{(end.month - 1) // 3 + 1}"
    used, pre = summarize(t, control_label)
    plot(t, used, pre, control_label, root / "analysis" / "figures" / "zhongli_trend.png")


if __name__ == "__main__":
    main()
