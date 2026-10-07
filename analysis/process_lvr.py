"""實價登錄「本期下載」zip → data/district_metrics.csv

用法：python analysis/process_lvr.py [專案資料夾]
- 讀 data/raw/ 底下（含子資料夾）所有 zip，各自解壓到同名資料夾（已解壓過且 zip 沒有更新就不重複解壓）
- 資料期間已經在 district_metrics.csv 裡的 zip 直接跳過
- 同一資料期間、縣市、行政區、指標已有資料就不重複寫入
"""
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

PING = 3.30579  # 1 坪 = 3.30579 平方公尺

RESIDENTIAL_TYPES = ("住宅大樓", "華廈", "公寓", "透天厝", "套房")

# 備註含這些字樣的視為特殊交易或異常案件，不列入單價統計
EXCLUDE_KEYWORDS = (
    "親友", "員工", "共有人", "特殊關係",
    "增建", "頂樓加蓋", "陽台外推", "夾層", "未登記建物",
    "分件登記", "協議價購", "政府機關", "公共設施保留地", "僅車位",
    "毛胚", "瑕疵", "急買急賣", "債權債務", "拍賣", "標售", "畸零地",
    "含傢俱", "含裝潢", "凶宅", "特殊",
)

OUT_COLUMNS = ["資料期間", "縣市", "行政區", "指標名稱", "數值"]


def roc_to_date(value):
    """民國年日期（1150902、0711130、11509）轉 date，無法解析回傳 None"""
    s = re.sub(r"\D", "", str(value or ""))
    try:
        if len(s) in (6, 7):
            s = s.zfill(7)
            return date(int(s[:3]) + 1911, int(s[3:5]), int(s[5:7]))
        if len(s) == 5:
            return date(int(s[:3]) + 1911, int(s[3:5]), 1)
    except ValueError:
        return None
    return None


def extract(zip_path):
    target = zip_path.with_suffix("")
    # 同名 zip 被新一期覆蓋時，資料夾會比 zip 舊，要重新解壓
    if not target.exists() or zip_path.stat().st_mtime > target.stat().st_mtime:
        target.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(target)
        target.touch()  # 更新資料夾時間，下次就不會重複解壓
    return target


def read_periods(folder):
    text = (folder / "build_time.xml").read_text(encoding="utf-8")

    def span(label):
        # 112 年的檔案寫成「登記日期自 111年12月11 至 112年3月10日」，多「自」、少「日」
        m = re.search(label + r"自?\s*(\d+)年(\d+)月(\d+)日?\s*至\s*(\d+)年(\d+)月(\d+)日", text)
        y1, m1, d1, y2, m2, d2 = map(int, m.groups())
        return f"{date(y1 + 1911, m1, d1)}~{date(y2 + 1911, m2, d2)}"

    return span("登記日期"), span("交易日期")


def read_main(folder, suffix, counties):
    frames = []
    for path in sorted(folder.glob(f"?_lvr_land_{suffix}.csv")):
        # 少數列最後一欄（如預售屋「棟及號」）含未加引號的逗號，多出來的欄位併回最後一欄
        n = len(pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns)
        df = pd.read_csv(
            path, encoding="utf-8-sig", skiprows=[1], dtype=str, engine="python",
            on_bad_lines=lambda row: row[: n - 1] + [",".join(row[n - 1:])],
        ).fillna("")
        df["縣市"] = counties[path.name]
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def prepare(df):
    num = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["總價"] = num("總價元")
    df["車位總價"] = num("車位總價元")
    df["建物面積"] = num("建物移轉總面積平方公尺")
    df["車位面積"] = num("車位移轉總面積平方公尺")

    df["住宅"] = (
        df["交易標的"].str.contains("建物")
        & df["建物型態"].str.startswith(RESIDENTIAL_TYPES)
        & df["主要用途"].str.contains("住")
    )
    pattern = "|".join(EXCLUDE_KEYWORDS)
    df["異常"] = df["備註"].str.contains(pattern)
    if "解約情形" in df.columns:
        df["異常"] |= df["解約情形"].str.strip() != ""

    # 扣除車位價格與面積後的每坪單價
    area = df["建物面積"] - df["車位面積"]
    price = df["總價"] - df["車位總價"]
    df["每坪單價"] = (price / area * PING).where((area > 0) & (price > 0))
    df.loc[df["每坪單價"].isna(), "異常"] = True
    return df


def house_age(df):
    trade = df["交易年月日"].map(roc_to_date)
    built = df["建築完成年月"].map(roc_to_date)
    return pd.Series(
        [(t - b).days / 365.25 if t and b and t >= b else None for t, b in zip(trade, built)],
        index=df.index, dtype=float,
    )


def metrics_for(sale, presale, presale_tag):
    # 成屋檔裡的分件登記多半是預售屋交屋，簽約時已列入預售屋，不算中古屋
    used = sale[sale["住宅"] & ~sale["預售交屋"]]
    pre = presale[presale["住宅"]]

    rows = {}
    rows["成屋買賣筆數"] = len(sale)
    rows[f"預售屋買賣筆數[{presale_tag}]"] = len(presale)

    for label, df, tag in (("中古屋", used, ""), ("預售屋", pre, f"[{presale_tag}]")):
        valid = df.loc[~df["異常"], "每坪單價"]
        rows[f"{label}住宅單價樣本數{tag}"] = len(valid)
        if len(valid):
            rows[f"{label}住宅每坪單價中位數(元){tag}"] = int(round(valid.median()))
            rows[f"{label}住宅每坪單價平均數(元){tag}"] = int(round(valid.mean()))

    n_used, n_pre = len(used), len(pre)
    if n_used + n_pre:
        rows[f"中古屋住宅成交比例(%)[{presale_tag}]"] = round(n_used / (n_used + n_pre) * 100, 1)
        rows[f"預售屋住宅成交比例(%)[{presale_tag}]"] = round(n_pre / (n_used + n_pre) * 100, 1)

    age = used["屋齡"].dropna()
    if len(age):
        rows["中古屋住宅屋齡樣本數"] = len(age)
        rows["屋齡5年內佔比(%)"] = round((age < 5).mean() * 100, 1)
        rows["屋齡5至20年佔比(%)"] = round(((age >= 5) & (age < 20)).mean() * 100, 1)
        rows["屋齡20年以上佔比(%)"] = round((age >= 20).mean() * 100, 1)
    return rows


def existing_periods(out):
    if not out.exists():
        return set()
    return set(pd.read_csv(out, encoding="utf-8-sig", dtype=str, usecols=["資料期間"])["資料期間"])


def process_zip(zip_path, out):
    folder = extract(zip_path)
    period, presale_period = read_periods(folder)
    if period in existing_periods(out):
        print(f"{zip_path.name}：資料期間 {period} 已處理過，跳過")
        return
    presale_tag = f"預售屋為交易日期{presale_period}"

    manifest = pd.read_csv(folder / "manifest.csv", encoding="utf-8-sig")
    counties = {
        r.name: re.sub(r"(不動產|建物|土地|停車場|預售屋|租賃).*$", "", r.description)
        for r in manifest.itertuples()
    }

    sale = prepare(read_main(folder, "a", counties))
    presale = prepare(read_main(folder, "b", counties))
    sale["屋齡"] = house_age(sale)
    sale["預售交屋"] = sale["備註"].str.contains("分件登記")

    groups = [("全國", "全區", sale, presale)]
    for county in sorted(set(sale["縣市"]) | set(presale["縣市"])):
        s, p = sale[sale["縣市"] == county], presale[presale["縣市"] == county]
        groups.append((county, "全區", s, p))
        for district in sorted(set(s["鄉鎮市區"]) | set(p["鄉鎮市區"])):
            groups.append((county, district, s[s["鄉鎮市區"] == district], p[p["鄉鎮市區"] == district]))

    records = [
        (period, county, district, name, str(value))
        for county, district, s, p in groups
        for name, value in metrics_for(s, p, presale_tag).items()
    ]
    new = pd.DataFrame(records, columns=OUT_COLUMNS, dtype=str)

    if out.exists():
        old = pd.read_csv(out, encoding="utf-8-sig", dtype=str)
        key = lambda df: df["資料期間"] + "|" + df["縣市"] + "|" + df["行政區"] + "|" + df["指標名稱"]
        new = new[~key(new).isin(set(key(old)))]
        new.to_csv(out, mode="a", header=False, index=False, encoding="utf-8")
    else:
        new.to_csv(out, index=False, encoding="utf-8-sig")

    res = sale[sale["住宅"]]
    used = res[~res["預售交屋"]]
    pre = presale[presale["住宅"]]
    print(f"{zip_path.name}：資料期間 {period}（{presale_tag}）")
    print(f"  成屋：全部 {len(sale)} 筆，住宅 {len(res)} 筆，其中預售屋交屋（分件登記）{int(res['預售交屋'].sum())} 筆不算中古屋")
    print(f"  中古屋住宅 {len(used)} 筆：單價統計排除異常 {int(used['異常'].sum())} 筆，採用 {int((~used['異常']).sum())} 筆")
    print(f"  預售屋：全部 {len(presale)} 筆，住宅 {len(pre)} 筆：單價統計排除異常 {int(pre['異常'].sum())} 筆，採用 {int((~pre['異常']).sum())} 筆")
    print(f"  寫入 {len(new)} 列到 {out}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    raw_dir = root / "data" / "raw"
    zips = sorted(raw_dir.rglob("*.zip"))  # 包含 2026Q2/ 這類子資料夾
    if not zips:
        sys.exit(f"找不到 zip：{raw_dir}")
    for zip_path in zips:
        process_zip(zip_path, root / "data" / "district_metrics.csv")


if __name__ == "__main__":
    main()
