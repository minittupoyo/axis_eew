import folium
import requests
import os
from playwright.sync_api import sync_playwright

url = "http://files.quake.one/20260420165303/largeScalePoints.json"

COLOR_MAP = {
    "7": "#AC09D4",  # 紫
    "6+": "#A50021", # 濃い赤
    "6-": "#FF2800", # 赤
    "5+": "#FF7B00", # 橙
    "5-": "#FFB400", # 黄橙
    "4": "#F2E700",  # 黄
    "3": "#0041FF",  # 青
    "2": "#0096FF",  # 水色
    "1": "#B4B4B4",   # 灰
    "epicenter": "#FF0000"
}

try:
    response = requests.get(url)
    response.raise_for_status()
    geojson_data = response.json()
except Exception as e:
    print(f"エラー: {e}")
    geojson_data = None

if geojson_data:
    features = geojson_data.get('features', [])

    center_coords = [38.5, 141.0]

    for feature in features:
        if feature['properties'].get('class') == 'epicenter':
            lon, lat = feature['geometry']['coordinates']
            center_coords = [lat,lon]
            break

    m = folium.Map(location=center_coords, zoom_start=7, tiles="CartoDB positron")

    all_coords = []
    for feature in features:
        props = feature['properties']
        cls = props.get('class')
        lon, lat = feature['geometry']['coordinates']

        if cls == 'epicenter':
            all_coords.append([lat, lon])
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup("震央", max_width=100),
                icon=folium.DivIcon(
                    icon_size=(30,30),
                    icon_anchor=(15,15),
                    html='<div style="font-size: 24pt; color: #FF0000; font-weight: bold; text-align: center; line-height: 30px;">×</div>',
                )
            ).add_to(m)
            continue

        if cls not in COLOR_MAP:
            continue

        all_coords.append([lat, lon])
        color = COLOR_MAP[cls]
        shindo = cls

        # 震度を中央に表示するカラーバッジ（DivIcon）
        icon = folium.DivIcon(
            icon_size=(24, 24),
            icon_anchor=(12, 12),
            html=f"""
                <div style="
                    background-color: {color};
                    color: white;
                    width: 12px;
                    height: 12px;
                    border-radius: 3px;
                    text-align: center;
                    line-height: 12px;
                    font-weight: bold;
                    font-size: 6px;
                    border: 1px solid #ffffff;
                " />
            """
        )

        folium.Marker(
            location=[lat, lon],
            icon=icon,
            popup=folium.Popup(f"{props.get('name')} 震度{shindo}", max_width=300)
        ).add_to(m)
    
    if all_coords:
        m.fit_bounds(all_coords)
    
    m.save("eq.html")
    print("eq.html に保存しました")

    # スクリーンショット撮影
    print("スクリーンショットを撮影中...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # 絶対パスを取得してブラウザで開く
        abs_path = "file://" + os.path.abspath("eq.html")
        page.goto(abs_path)
        # ネットワークが安定するまで（タイルの読み込み等）待機
        page.wait_for_load_state("networkidle")
        # 地図のレンダリング時間を考慮して少し待つ（任意）
        page.wait_for_timeout(1000) 
        page.screenshot(path="eq.png", full_page=True)
        browser.close()
    
    print("eq.png にスクリーンショットを保存しました")