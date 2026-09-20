import os
import json
import requests

# 1. 服务器候选列表与请求头配置
POST_URLS = [
    "47.99.202.156:8003",
    "38.75.136.137:82",
    "47.97.252.137:81",
    "198.204.226.146:88",
    "107.150.35.234:88"
]

USER_AGENT = "AppleCoreMedia/1.0.0.15F79 (iPhone; U; CPU OS 11_4 like Mac OS X; zh_cn)"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Range": "bytes=0-",
    "Connection": "close",
    "Icy-MetaData": "1"
}

def load_categories_from_xml(json_file="channel_aliases.xml"):
    """
    直接从 channel_aliases.xml (JSON 格式) 读取分类和频道信息
    返回结构:
    [
        {
            "category": "中央频道",
            "name": "CCTV-1综合",
            "api_id": "cctv1"
        },
        ...
    ]
    """
    if not os.path.exists(json_file):
        print(f"❌ 未找到文件: {json_file}")
        return []

    channel_list = []
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for cat in data.get("categories", []):
                cat_name = cat.get("name", "未分类").strip()
                for ch in cat.get("channels", []):
                    ch_name = ch.get("note", "").strip()
                    epgid = ch.get("epgid", "").strip()
                    if ch_name and epgid:
                        channel_list.append({
                            "category": cat_name,
                            "name": ch_name,
                            "api_id": epgid
                        })
        print(f"✅ 成功从 {json_file} 加载 {len(channel_list)} 个频道！")
    except Exception as e:
        print(f"❌ 解析 {json_file} 失败: {e}")

    return channel_list

def fetch_m3u8_url(api_id):
    """
    轮询 POST_URLS 中的每一个服务器，抓取真实 m3u8 地址。
    如果获取成功则立即返回；若所有服务器都失败，返回 None。
    """
    for server_host in POST_URLS:
        target_url = f"http://{server_host}/apptv/{api_id}.m3u8"
        try:
            res = requests.get(target_url, headers=HEADERS, allow_redirects=False, timeout=3)
            if res.status_code == 302 and "Location" in res.headers:
                return res.headers["Location"]
            elif res.status_code == 200:
                return target_url
        except Exception:
            continue
            
    return None

def export_m3u(channel_list, output_file="live_playlist.m3u"):
    """生成 M3U 文件，仅包含成功获取到链接的频道，严格格式化输出"""
    m3u_lines = ["#EXTM3U\n"]
    print("\n正在获取直播源地址并生成播放列表...")

    success_count = 0
    fail_count = 0

    for idx, ch in enumerate(channel_list, 1):
        real_url = fetch_m3u8_url(ch["api_id"])
        
        if real_url:
            success_count += 1
            print(f"[{idx:02d}] {ch['category']} -> {ch['name']} : ✔")

            # 按照指定的格式拼接：
            # #EXTINF:-1 tvg-name="名称", group-title="分类" , 名称
            # #EXTVLCOPT:http-user-agent=...
            # URL
            extinf = f'#EXTINF:-1 tvg-name="{ch["name"]}", group-title="{ch["category"]}" ,{ch["name"]}'
            opt = f'#EXTVLCOPT:http-user-agent={USER_AGENT}'

            m3u_lines.append(extinf)
            m3u_lines.append(opt)
            m3u_lines.append(f"{real_url}\n")
        else:
            fail_count += 1
            print(f"[{idx:02d}] {ch['category']} -> {ch['name']} : ✖ (无有效链接，跳过)")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
        
    print(f"\n✅ 导出完成！成功写入 {success_count} 个频道，跳过 {fail_count} 个无效频道。")
    print(f"📁 文件已保存为: {output_file}")

def main():
    # 仅读取 channel_aliases.xml
    channel_list = load_categories_from_xml("channel_aliases.xml")
    if not channel_list:
        return

    # 生成并导出 M3U
    export_m3u(channel_list)

if __name__ == "__main__":
    main()