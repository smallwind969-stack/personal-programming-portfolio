from pathlib import Path
import csv

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def read_locations():
    with (DATA / "locations.csv").open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        result = {}
        for row in reader:
            result[row["编号"]] = {
                "id": row["编号"],
                "name": row["名称"],
                "x": float(row["横坐标"]),
                "y": float(row["纵坐标"]),
                "category": row["类别"],
            }
        return result


def read_roads():
    with (DATA / "roads.csv").open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def scale(point):
    x, y = point
    return int(x * 1.42 + 55), int(y * 1.32 + 100)


def midpoint(a, b):
    return (a[0] + b[0]) // 2, (a[1] + b[1]) // 2


def edge_key(a, b):
    return tuple(sorted((a, b), key=lambda value: int(value)))


def main():
    locations = read_locations()
    roads = read_roads()
    route_edges = {edge_key("1", "5"), edge_key("5", "7"), edge_key("7", "8")}
    mst_edges = {
        edge_key("3", "5"),
        edge_key("3", "4"),
        edge_key("7", "6"),
        edge_key("2", "11"),
        edge_key("9", "12"),
        edge_key("7", "8"),
        edge_key("1", "2"),
        edge_key("12", "8"),
        edge_key("2", "3"),
        edge_key("4", "9"),
        edge_key("8", "10"),
    }

    image = Image.new("RGB", (1180, 740), "#f7f8f3")
    draw = ImageDraw.Draw(image)
    title_font = load_font(30, True)
    subtitle_font = load_font(18)
    label_font = load_font(15, True)
    small_font = load_font(13)
    weight_font = load_font(14, True)

    draw.text((38, 28), "智慧校园图算法实验平台地图", fill="#243447", font=title_font)
    draw.text((40, 72), "蓝色：当前最短路线（学校正门 → 学生宿舍）  绿色：最小道路改造网络  灰色：普通道路",
              fill="#546476", font=subtitle_font)

    draw.rounded_rectangle((32, 610, 1148, 705), radius=12, fill="#ffffff", outline="#d5dde5", width=2)
    draw.text((52, 628), "推荐演示：选择功能 2，起点输入 1，终点输入 8。系统将计算：学校正门 → 第一教学楼 → 学生食堂 → 学生宿舍，总权值 23。",
              fill="#263645", font=subtitle_font)
    draw.text((52, 666), "说明：地图用于课程设计中的图结构建模，地点和道路权值均存放在 data 目录，可替换为真实测量数据。",
              fill="#536170", font=small_font)

    for road in roads:
        a = locations[road["起点"]]
        b = locations[road["终点"]]
        p1 = scale((a["x"], a["y"]))
        p2 = scale((b["x"], b["y"]))
        key = edge_key(road["起点"], road["终点"])
        if key in route_edges:
            color, width = "#006dff", 8
        elif key in mst_edges:
            color, width = "#1f9d55", 5
        else:
            color, width = "#b8c0c8", 3
        draw.line((p1, p2), fill=color, width=width)
        mx, my = midpoint(p1, p2)
        draw.rounded_rectangle((mx - 13, my - 12, mx + 13, my + 12), radius=6, fill="#ffffff", outline="#d5dde5")
        draw.text((mx - 5, my - 9), road["权值"], fill="#243447", font=weight_font)

    for loc_id in sorted(locations, key=lambda value: int(value)):
        loc = locations[loc_id]
        x, y = scale((loc["x"], loc["y"]))
        is_route = loc_id in {"1", "5", "7", "8"}
        fill = "#006dff" if is_route else "#ffffff"
        outline = "#102b4e" if is_route else "#243447"
        draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=fill, outline=outline, width=3)
        draw.text((x - 6 if len(loc_id) == 1 else x - 11, y - 10), loc_id,
                  fill="#ffffff" if is_route else "#243447", font=label_font)
        draw.text((x + 18, y - 18), loc["name"], fill="#243447", font=label_font)
        draw.text((x + 18, y + 2), loc["category"], fill="#687684", font=small_font)

    output = OUTPUT / "campus_map.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    main()
