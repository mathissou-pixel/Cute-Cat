import tkinter as tk
from tkinter import messagebox
import urllib.request
import os
import random
import ctypes
import xml.etree.ElementTree as ET
from PIL import Image, ImageTk, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_URL = "https://www.image2url.com/r2/default/audio/1794650917103-f8cb0270-4dda-4a7c-aee5-4a67b5cec76e.mp3"
AUDIO_FILE = os.path.join(BASE_DIR, "meow.mp3")
XML_FILE = os.path.join(BASE_DIR, "chats.xml")
TRANS_COLOR = "#00ff01"

def play_meow():
    try:
        if not os.path.exists(AUDIO_FILE):
            req = urllib.request.Request(AUDIO_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(AUDIO_FILE, 'wb') as f:
                f.write(resp.read())
        ctypes.windll.winmm.mciSendStringW("close meow", None, 0, 0)
        ctypes.windll.winmm.mciSendStringW(f"open \"{os.path.abspath(AUDIO_FILE)}\" type mpegvideo alias meow", None, 0, 0)
        ctypes.windll.winmm.mciSendStringW("play meow", None, 0, 0)
    except Exception:
        pass

def parse_xml_config():
    if not os.path.exists(XML_FILE):
        raise FileNotFoundError(f"Le fichier XML « {XML_FILE} » est introuvable.")
    
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    image_name = os.path.join(BASE_DIR, root.get("image", "cats_sheet.png"))
    cols = int(root.get("columns", 4))
    rows = int(root.get("rows", 2))
    
    sprites = []
    for sprite in root.findall("sprite"):
        sprites.append({
            "id": int(sprite.get("id")),
            "name": sprite.get("name")
        })
    return image_name, cols, rows, sprites

class CatSelector:
    def __init__(self, sprites_data):
        self.selected_cat = 0
        self.root = tk.Tk()
        self.root.title("Choisis ton chat")
        self.root.attributes("-topmost", True)
        self.root.config(bg="#222222")
        self.root.resizable(False, False)

        tk.Label(self.root, text="Choisis ton compagnon", fg="white", bg="#222222", font=("Segoe UI", 12, "bold")).pack(pady=10)

        frame = tk.Frame(self.root, bg="#222222")
        frame.pack(padx=10, pady=10)

        for i, data in enumerate(sprites_data):
            row = i // 4
            col = i % 4
            btn = tk.Button(
                frame, text=data["name"], width=12, height=2,
                bg="#333333", fg="white", activebackground="#f07828", activeforeground="white",
                command=lambda idx=data["id"]: self.choose(idx)
            )
            btn.grid(row=row, column=col, padx=5, pady=5)

        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

        self.root.mainloop()

    def choose(self, idx):
        self.selected_cat = idx
        self.root.destroy()

class DesktopCat:
    def __init__(self, cat_index=0):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANS_COLOR)
        self.root.config(bg=TRANS_COLOR)

        self.cat_index = cat_index
        self.img_right, self.img_left, self.yarn_img = self.load_assets(cat_index)
        self.cat_w = self.img_right.width()
        self.cat_h = self.img_right.height()

        self.pad_x = 30
        self.pad_top = 35
        self.win_w = self.cat_w + self.pad_x * 2
        self.win_h = self.cat_h + self.pad_top

        self.canvas = tk.Canvas(
            self.root,
            width=self.win_w,
            height=self.win_h,
            bg=TRANS_COLOR,
            highlightthickness=0
        )
        self.canvas.pack()

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.floor_y = self.screen_h - self.win_h - 45

        self.x = self.screen_w // 2
        self.y = self.floor_y
        self.vy = 0

        self.state = "idle"
        self.direction = 1
        self.frame = 0
        self.state_timer = 40
        self.chase_mode = False
        self.food_x = None
        self.yarn_x = None
        self.yarn_vx = 0
        self.particles = []

        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.pet_cat)
        self.canvas.bind("<MouseWheel>", self.pet_cat)
        self.canvas.bind("<Button-3>", self.show_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Changer de chat", command=self.open_selector_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Lancer la pelote de laine", command=self.spawn_yarn)
        self.menu.add_command(label="Ranger la pelote", command=self.clear_yarn)
        self.menu.add_command(label="Donner un poisson", command=self.spawn_food)
        self.menu.add_command(label="Chasser la souris", command=self.toggle_chase)
        self.menu.add_command(label="Coup de folie", command=self.trigger_zoomies)
        self.menu.add_command(label="Dormir / Réveiller", command=self.toggle_sleep)
        self.menu.add_separator()
        self.menu.add_command(label="Quitter", command=self.root.destroy)

        self.update_position()
        self.update()
        self.root.mainloop()

    def load_assets(self, index=0):
        def apply_chroma_key(rgba_img):
            bg = Image.new("RGBA", rgba_img.size, (0, 255, 1, 255))
            alpha = rgba_img.split()[3].point(lambda p: 255 if p > 128 else 0)
            rgba_img.putalpha(alpha)
            return Image.alpha_composite(bg, rgba_img).convert("RGB")

        image_path, cols, rows, sprites = parse_xml_config()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"L'image « {image_path} » est introuvable.")

        sheet = Image.open(image_path).convert("RGBA")

        # Découpage dynamique basé sur la taille réelle de l'image
        cw = sheet.width // cols
        ch = sheet.height // rows
        col = index % cols
        row = index // cols
        box = (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)

        img = sheet.crop(box)
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        target_height = 95
        ratio = target_height / img.height
        target_width = int(img.width * ratio)
        img = img.resize((target_width, target_height), Image.Resampling.NEAREST)

        img_right = ImageTk.PhotoImage(apply_chroma_key(img.copy()))
        img_left = ImageTk.PhotoImage(apply_chroma_key(ImageOps.mirror(img.copy())))

        return img_right, img_left, None

    def add_particle(self, x, y, text, color="#ff4d6d", life=15):
        self.particles.append([x, y, text, color, life])

    def update_position(self):
        self.root.geometry(f"{self.win_w}x{self.win_h}+{int(self.x)}+{int(self.y)}")

    def draw_cat(self):
        self.canvas.delete("all")
        bounce = 0
        if self.state == "walk":
            bounce = -4 if self.frame % 2 == 1 else 0
        elif self.state in ("run", "chase", "eat", "yarn"):
            bounce = -8 if self.frame % 2 == 1 else 0
        elif self.state == "drag":
            bounce = -3 if self.frame % 2 == 1 else 3

        sprite = self.img_right if self.direction == 1 else self.img_left
        self.canvas.create_image(self.pad_x, self.pad_top + bounce, anchor="nw", image=sprite)

        if self.food_x is not None:
            rel_food_x = self.food_x - self.x
            if 0 <= rel_food_x <= self.win_w:
                self.canvas.create_text(rel_food_x, self.win_h - 15, text="🐟", font=("Segoe UI Emoji", 14))

        if self.yarn_x is not None:
            rel_yarn_x = self.yarn_x - self.x
            if -30 <= rel_yarn_x <= self.win_w + 30:
                self.canvas.create_text(rel_yarn_x, self.win_h - 15, text="🧶", font=("Segoe UI Emoji", 14))

        for p in self.particles[:]:
            px, py, ptext, pcolor, plife = p
            self.canvas.create_text(px, py, text=ptext, fill=pcolor, font=("Courier", 11, "bold"))
            p[1] -= 1.5
            p[4] -= 1
            if p[4] <= 0:
                self.particles.remove(p)

    def update(self):
        self.frame += 1

        if self.yarn_x is not None:
            self.yarn_x += self.yarn_vx
            if self.yarn_x <= 15:
                self.yarn_x = 15
                self.yarn_vx = -self.yarn_vx * 0.75
            elif self.yarn_x >= self.screen_w - 15:
                self.yarn_x = self.screen_w - 15
                self.yarn_vx = -self.yarn_vx * 0.75
            
            self.yarn_vx *= 0.95
            if abs(self.yarn_vx) < 0.3:
                self.yarn_vx = 0

        if self.state == "fall":
            self.vy += 3
            self.y += self.vy
            if self.y >= self.floor_y:
                self.y = self.floor_y
                self.vy = 0
                self.state = "idle"
                self.state_timer = 20
                self.add_particle(self.win_w // 2, self.win_h - 10, "pouf!", "#888888", 8)
            self.update_position()

        elif self.state != "drag":
            if self.yarn_x is not None:
                self.state = "yarn"
                cat_center_x = self.x + self.win_w // 2
                diff = self.yarn_x - cat_center_x
                if abs(diff) > 15:
                    self.direction = 1 if diff > 0 else -1
                    self.x += 11 * self.direction
                else:
                    self.yarn_vx = self.direction * random.randint(12, 18)
                    play_meow()
                    for _ in range(2):
                        self.add_particle(random.randint(30, self.win_w - 30), random.randint(15, 35), "✨", "#f59e0b", 10)
                self.update_position()

            elif self.food_x is not None:
                self.state = "eat"
                cat_center_x = self.x + self.win_w // 2
                diff = self.food_x - cat_center_x
                if abs(diff) > 10:
                    self.direction = 1 if diff > 0 else -1
                    self.x += 9 * self.direction
                else:
                    self.food_x = None
                    self.state = "idle"
                    self.state_timer = 30
                    play_meow()
                    for _ in range(3):
                        self.add_particle(random.randint(30, self.win_w - 30), random.randint(15, 35), "♥", "#ff4d6d", 14)
                self.update_position()

            elif self.chase_mode:
                self.state = "chase"
                mouse_x = self.root.winfo_pointerx()
                cat_center_x = self.x + self.win_w // 2
                diff = mouse_x - cat_center_x
                if abs(diff) > 15:
                    self.direction = 1 if diff > 0 else -1
                    self.x += 10 * self.direction
                self.update_position()

            else:
                self.state_timer -= 1
                if self.state_timer <= 0:
                    self.choose_next_state()

                if self.state == "walk":
                    self.move_horizontal(4)
                elif self.state == "run":
                    self.move_horizontal(11)
                elif self.state == "sleep" and self.frame % 8 == 0:
                    self.add_particle(self.win_w - 25, 25, "zZz", "#6e6a86", 12)

        self.draw_cat()
        self.root.after(100, self.update)

    def move_horizontal(self, speed):
        self.x += speed * self.direction
        if self.x <= 5:
            self.x = 5
            self.direction = 1
        elif self.x >= self.screen_w - self.win_w - 5:
            self.x = self.screen_w - self.win_w - 5
            self.direction = -1
        self.update_position()

    def choose_next_state(self):
        choice = random.choices(["idle", "walk", "run", "sleep"], weights=[40, 35, 10, 15])[0]
        self.state = choice
        if choice == "walk":
            self.direction = random.choice([-1, 1])
            self.state_timer = random.randint(20, 50)
        elif choice == "run":
            self.direction = random.choice([-1, 1])
            self.state_timer = random.randint(15, 30)
        elif choice == "sleep":
            self.state_timer = random.randint(50, 110)
        else:
            self.state_timer = random.randint(25, 60)

    def on_click(self, event):
        if self.yarn_x is not None:
            rel_yarn_x = self.yarn_x - self.x
            if rel_yarn_x <= event.x <= rel_yarn_x + 35:
                self.clear_yarn()
                return

        self.state = "drag"
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y

    def on_drag(self, event):
        if self.state == "drag":
            self.x = self.root.winfo_x() + event.x - self.drag_offset_x
            self.y = self.root.winfo_y() + event.y - self.drag_offset_y
            self.update_position()

    def on_release(self, event):
        if self.state == "drag":
            if self.y < self.floor_y - 10:
                self.state = "fall"
                self.vy = 0
            else:
                self.y = self.floor_y
                self.state = "idle"
                self.state_timer = 20
                play_meow()
                self.update_position()

    def pet_cat(self, event):
        play_meow()
        self.add_particle(random.randint(self.pad_x, self.win_w - self.pad_x), random.randint(15, 35), "♥", "#ff4d6d", 12)

    def spawn_food(self):
        self.food_x = max(50, min(self.screen_w - 50, self.x + random.choice([-180, 180])))

    def spawn_yarn(self):
        self.yarn_x = max(50, min(self.screen_w - 50, self.x + random.choice([-200, 200])))
        self.yarn_vx = random.choice([-12, 12])

    def clear_yarn(self):
        self.yarn_x = None
        self.yarn_vx = 0
        if self.state == "yarn":
            self.state = "idle"
            self.state_timer = 20

    def toggle_chase(self):
        self.chase_mode = not self.chase_mode
        if not self.chase_mode:
            self.state = "idle"
            self.state_timer = 20

    def trigger_zoomies(self):
        self.state = "run"
        self.direction = random.choice([-1, 1])
        self.state_timer = 35

    def toggle_sleep(self):
        self.chase_mode = False
        self.state = "idle" if self.state == "sleep" else "sleep"
        self.state_timer = 80

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def open_selector_menu(self):
        self.root.destroy()
        main()

def main():
    try:
        _, _, _, sprites = parse_xml_config()
        selector = CatSelector(sprites)
        chosen_index = selector.selected_cat
        
        DesktopCat(chosen_index)
    except Exception as e:
        err_root = tk.Tk()
        err_root.withdraw()
        messagebox.showerror("Erreur de lancement", str(e))

if __name__ == "__main__":
    main()