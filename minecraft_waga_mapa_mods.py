import os
import requests
import time
from datetime import datetime
import anvil
from PIL import Image
import base64

# ================== USTAWIENIA ==================
WORLD_PATH = r"C:\Users\TWÓJ_USER\AppData\Roaming\.minecraft\saves\NazwaTwojegoŚwiata"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/TWOJ_WEBHOOK_TUTAJ"

# GITHub - OBOWIĄZKOWE (bo mapy tylko tam)
GITHUB_TOKEN = "ghp_TWÓJ_TOKEN_TUTAJ"          # <-- wklej swój token
GITHUB_REPO = "TwojNick/minecraft-world-map"   # <-- user/repo

INTERVAL_SECONDS = 3600
MAP_SIZE = 1024                                # 1024 bloków = duża mapa (da się!)
# ================================================

def ile_wazy_tylko_regiony(sciezka):
    total = 0
    for dim in ["", "DIM-1", "DIM1"]:
        folder = os.path.join(sciezka, dim, "region") if dim else os.path.join(sciezka, "region")
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".mca"):
                    total += os.path.getsize(os.path.join(folder, f))
    return total

def get_biome_color(block_name, dimension=""):
    # Obsługa modów - bierzemy tylko nazwę po ostatnim ":" 
    clean = block_name.split(":")[-1]
    colors = {
        "" : {  # Overworld biomes
            "grass_block": (50, 180, 50), "dirt": (139, 90, 40), "stone": (110, 110, 110),
            "water": (30, 100, 180), "sand": (220, 200, 100), "oak_log": (100, 60, 30),
            "leaves": (30, 140, 30), "snow_block": (240, 240, 240),
        },
        "DIM-1" : {  # Nether biomes
            "netherrack": (140, 20, 20), "soul_sand": (80, 60, 40), "basalt": (50, 50, 60),
            "lava": (255, 100, 0),
        },
        "DIM1" : {  # End biomes
            "end_stone": (220, 220, 180), "purpur_block": (180, 120, 180),
        }
    }
    paleta = colors.get(dimension, colors[""])
    return paleta.get(clean, (90, 90, 90))  # szary = modowy blok

def generate_map_image(sciezka, dim_folder="", output="map.png"):
    full_path = os.path.join(sciezka, dim_folder) if dim_folder else sciezka
    region_folder = os.path.join(full_path, "region")
    img = Image.new("RGB", (MAP_SIZE, MAP_SIZE), (20, 20, 40))
    chunk_radius = MAP_SIZE // 16

    print(f"🗺 Generuję {dim_folder or 'Overworld'} ({MAP_SIZE}x{MAP_SIZE})...")
    for cx in range(-chunk_radius, chunk_radius):
        for cz in range(-chunk_radius, chunk_radius):
            rx, rz = cx // 32, cz // 32
            local_cx, local_cz = cx % 32, cz % 32
            region_file = os.path.join(region_folder, f"r.{rx}.{rz}.mca")
            if not os.path.exists(region_file):
                continue
            try:
                region = anvil.Region.from_file(region_file)
                chunk = anvil.Chunk.from_region(region, local_cx, local_cz)
                for lx in range(16):
                    for lz in range(16):
                        y_start = 319 if not dim_folder else (127 if dim_folder == "DIM-1" else 255)
                        for y in range(y_start, -64, -1):
                            block = chunk.get_block(lx, y, lz)
                            if block.name != "minecraft:air" and block.name != "minecraft:cave_air":
                                color = get_biome_color(block.name, dim_folder)
                                px = (cx * 16 + lx) + (MAP_SIZE // 2)
                                pz = (cz * 16 + lz) + (MAP_SIZE // 2)
                                if 0 <= px < MAP_SIZE and 0 <= pz < MAP_SIZE:
                                    img.putpixel((px, pz), color)
                                break
            except:
                pass
    img.save(output)
    return output

def upload_to_github(file_path, filename):
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/maps/{filename}"
    data = {
        "message": f"Auto update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "branch": "main"
    }
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.put(url, json=data, headers=headers)
    if r.status_code in (200, 201):
        return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/maps/{filename}"
    print("GitHub błąd:", r.text)
    return "Błąd uploadu"

def wyslij_na_discord(rozmiar, linki):
    mb = rozmiar / (1024 * 1024)
    gb = mb / 1024
    teraz = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    msg = f"""**📦 Rozmiar świata Minecraft:**
**{rozmiar:,} B** | **{mb:,.2f} MB** | **{gb:,.3f} GB**
🕒 {teraz}

**🗺 Mapa live (tylko na GitHub):**
Overworld → {linki[0]}
Nether → {linki[1]}
End → {linki[2]}"""

    requests.post(DISCORD_WEBHOOK, json={"content": msg, "username": "Minecraft World + Live Map"})

print("🤖 BOT MODS + MAPA + GITHUB START!")
while True:
    try:
        waga = ile_wazy_tylko_regiony(WORLD_PATH)
        linki = []
        for dim_name, dim_folder in [("Overworld", ""), ("Nether", "DIM-1"), ("End", "DIM1")]:
            plik = f"map_{dim_name.lower()}.png"
            generate_map_image(WORLD_PATH, dim_folder, plik)
            link = upload_to_github(plik, plik)
            linki.append(link)
        wyslij_na_discord(waga, linki)
    except Exception as e:
        print("Błąd:", e)
    
    print(f"⏳ Następne w {INTERVAL_SECONDS//60} minut...")
    time.sleep(INTERVAL_SECONDS)