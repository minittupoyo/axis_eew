import asyncio
import websockets
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("AXIS_TOKEN")

def get_axis_server():
    url = "https://axis.prioris.jp/api/server/list/"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        servers = res.json().get("servers", [])
        return f"{servers[0].rstrip('/')}/socket" if servers else None
    except Exception as e:
        print(f"サーバーリスト取得失敗: {e}")
        return None

async def axis_subscriber():
    uri = get_axis_server()
    if not uri: return

    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        async with websockets.connect(uri, additional_headers=headers) as ws:
            print(f"Connected to {uri}")

            first_msg = await ws.recv()
            if first_msg == "hello":
                print("Handshake success")

            async def heartbeat():
                while True:
                    await asyncio.sleep(60)
                    await ws.send("hb")
            
            hb_task = asyncio.create_task(heartbeat())

            try:
                async for message in ws:
                    if message == "hb": continue
                    
                    try:
                        data = json.loads(message)
                        if data.get("channel") == "eew":
                            body = data.get("message", {})
                            
                            flags = body.get("Flag", {})
                            is_final = flags.get("is_final", False)
                            is_cancel = flags.get("is_cancel", False)
                            is_training = flags.get("is_training", False)
                            
                            title = body.get("Title", "緊急地震速報")
                            prefix = "【訓練】" if is_training else ""

                            if is_cancel:
                                print(f"{prefix}{title}: キャンセルされました")
                                continue

                            hypo = body.get("Hypocenter", {})
                            hypo_name = hypo.get("Name", "不明")
                            depth = hypo.get("Depth", "不明")
                            mag = body.get("Magnitude", "不明")
                            intensity = body.get("Intensity", "不明")
                            origin_time = body.get("OriginDateTime")

                            dt_str = datetime.fromisoformat(origin_time).strftime('%Y/%m/%d %H:%M:%S') if origin_time else "不明"
                            
                            status = "最終報" if is_final else f"第{body.get('Serial', '?')}報"

                            print("-"*30)
                            print(f"\n{prefix}{title} ({status})")
                            print(f"発生時刻：{dt_str}")
                            print(f"震源地：{hypo_name} (深さ:{depth})")
                            print(f"マグニチュード：M{mag} / 最大震度：{intensity}")
                            print("-"*30)
                    except json.JSONDecodeError:
                        pass
            finally:
                hb_task.cancel()

    except Exception as e:
        print(f"Connection error: {e}")

async def main():
    if not TOKEN:
        print("AXIS_TOKEN が設定されていません")
        return
    while True:
        await axis_subscriber()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())