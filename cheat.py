import pymem
import pymem.process
import time
import os
import threading
import keyboard
import struct
import math
import win32gui
import tkinter as tk

PROCESS_NAME = "FPVKamikazeDrone-Win64-Shipping.exe"
GAME_WINDOW_CLASS = "UnrealWindow"

# --- Клавиши управления ---
KEY_FLY_MODE = "f3"
KEY_SUPER_SPEED = "f6"
KEY_SPIDERMAN = "f8"
KEY_AIR_CONTROL = "f9"
KEY_WALLHACK = "f11"
KEY_EXIT = "end"

GWORLD = 0x9817498
PERSISTENT_LEVEL = 0x0030
OWNING_GAME_INSTANCE = 0x1D8
LOCAL_PLAYERS = 0x38
PLAYER_CONTROLLER = 0x30
ACKNOWLEDGED_PAWN = 0x350 
ROOT_COMPONENT = 0x01B8
RELATIVE_LOCATION = 0x0128
CHARACTER_MOVEMENT_OFFSET = 0x0330 

ACTORS_ARRAY = 0xA0
PLAYER_CAMERA_MANAGER_OFFSET = 0x0360
CAMERA_CACHE_OFFSET = 0x1410
POV_OFFSET = 0x0010
PLAYER_STATE_IN_PAWN_OFFSET = 0x02C8 
IS_BOT_FLAG_OFFSET = 0x02B2
PLAYER_NAME_OFFSET = 0x0340

MOVEMENT_MODE_OFFSET = 0x0221
GRAVITY_SCALE_OFFSET = 0x0188
MAX_WALK_SPEED_OFFSET = 0x0268
MAX_FLY_SPEED_OFFSET = 0x0274
AIR_CONTROL_OFFSET = 0x02A0
WALKABLE_FLOOR_ANGLE_OFFSET = 0x01B4

MOVE_WALKING = 1
MOVE_FLYING = 5

cheat_states = {
    "fly_mode": False,
    "super_speed": False,
    "spiderman": False,
    "air_control": False,
    "wallhack": False,
}

original_values = {
    "walk_speed": 600.0,
    "fly_speed": 600.0,
    "air_control": 0.2,
    "gravity": 1.0,
    "floor_angle": 45.0,
}

stop_event = threading.Event()

wh_targets_on_screen = []
wh_known_targets = {}
wh_gui_thread = None
wh_scanner_thread = None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    clear_console()
    print("╔═════════════════════════════════════════════════════════╗")
    print("║            🔥 FPV Menu by Мафиозник 🔥                 ║")
    print("╠═════════════════════════════════════════════════════════╣")
    
    status_fly = "АКТИВЕН" if cheat_states["fly_mode"] else "ВЫКЛ"
    status_speed = "АКТИВЕН" if cheat_states["super_speed"] else "ВЫКЛ"
    status_spider = "АКТИВЕН" if cheat_states["spiderman"] else "ВЫКЛ"
    status_air = "АКТИВЕН" if cheat_states["air_control"] else "ВЫКЛ"
    status_wh = "АКТИВЕН" if cheat_states["wallhack"] else "ВЫКЛ"
    
    print(f"║ [{KEY_FLY_MODE.upper()}]  - Режим Полета (HOST)        | Статус: {status_fly:<10} ║")
    print(f"║ [{KEY_SUPER_SPEED.upper()}] - Супер-скорость(HOST)        | Статус: {status_speed:<10} ║")
    print(f"║ [{KEY_SPIDERMAN.upper()}] - Режим Spider-Man(HOST)      | Статус: {status_spider:<10} ║")
    print(f"║ [{KEY_AIR_CONTROL.upper()}] - Контроль в воздухе(HOST)    | Статус: {status_air:<10} ║")
    print(f"║ [{KEY_WALLHACK.upper()}] - Wallhack                   | Статус: {status_wh:<10} ║")
    print("╠═════════════════════════════════════════════════════════╣")
    print(f"║ Нажмите [{KEY_EXIT.upper()}] для безопасного выхода из программы.      ║")
    print("╚═════════════════════════════════════════════════════════╝")

def get_pointers(pm, base_address):
    try:
        world_ptr = pm.read_longlong(base_address + GWORLD)
        game_instance_ptr = pm.read_longlong(world_ptr + OWNING_GAME_INSTANCE)
        local_players_array_ptr = pm.read_longlong(game_instance_ptr + LOCAL_PLAYERS)
        local_player_ptr = pm.read_longlong(local_players_array_ptr)
        player_controller_ptr = pm.read_longlong(local_player_ptr + PLAYER_CONTROLLER)
        player_pawn_ptr = pm.read_longlong(player_controller_ptr + ACKNOWLEDGED_PAWN)
        movement_comp_ptr = pm.read_longlong(player_pawn_ptr + CHARACTER_MOVEMENT_OFFSET)
        return player_pawn_ptr, movement_comp_ptr
    except (pymem.exception.MemoryReadError, TypeError):
        return None, None

def movement_cheats_worker(pm, base_address):
    initialized = False
    
    while not stop_event.is_set():
        time.sleep(0.01)
        
        _, movement_comp_ptr = get_pointers(pm, base_address)
        if not movement_comp_ptr:
            initialized = False
            continue

        if not initialized:
            try:
                original_values["walk_speed"] = pm.read_float(movement_comp_ptr + MAX_WALK_SPEED_OFFSET)
                original_values["fly_speed"] = pm.read_float(movement_comp_ptr + MAX_FLY_SPEED_OFFSET)
                original_values["air_control"] = pm.read_float(movement_comp_ptr + AIR_CONTROL_OFFSET)
                original_values["gravity"] = pm.read_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET)
                original_values["floor_angle"] = pm.read_float(movement_comp_ptr + WALKABLE_FLOOR_ANGLE_OFFSET)
                if original_values["walk_speed"] > 10:
                    initialized = True
            except pymem.exception.MemoryReadError:
                continue

        try:
            if cheat_states["fly_mode"]:
                pm.write_uchar(movement_comp_ptr + MOVEMENT_MODE_OFFSET, MOVE_FLYING)
                pm.write_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET, 0.0)
                pm.write_float(movement_comp_ptr + MAX_FLY_SPEED_OFFSET, 3000.0)
            else:
                if pm.read_uchar(movement_comp_ptr + MOVEMENT_MODE_OFFSET) == MOVE_FLYING:
                    pm.write_uchar(movement_comp_ptr + MOVEMENT_MODE_OFFSET, MOVE_WALKING)
                    pm.write_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET, original_values["gravity"])
                    pm.write_float(movement_comp_ptr + MAX_FLY_SPEED_OFFSET, original_values["fly_speed"])

            # 2. Super Speed
            if cheat_states["super_speed"]:
                pm.write_float(movement_comp_ptr + MAX_WALK_SPEED_OFFSET, original_values["walk_speed"] * 5.0)
            else:
                pm.write_float(movement_comp_ptr + MAX_WALK_SPEED_OFFSET, original_values["walk_speed"])

            # 3. Spider-Man
            if cheat_states["spiderman"]:
                pm.write_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET, 0.0)
                pm.write_float(movement_comp_ptr + WALKABLE_FLOOR_ANGLE_OFFSET, 90.0)
            elif not cheat_states["fly_mode"]: # Не восстанавливать гравитацию, если включен полет
                 if pm.read_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET) == 0.0:
                    pm.write_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET, original_values["gravity"])
                    pm.write_float(movement_comp_ptr + WALKABLE_FLOOR_ANGLE_OFFSET, original_values["floor_angle"])

            # 4. Air Control
            if cheat_states["air_control"]:
                pm.write_float(movement_comp_ptr + AIR_CONTROL_OFFSET, 1.0)
            else:
                pm.write_float(movement_comp_ptr + AIR_CONTROL_OFFSET, original_values["air_control"])
        
        except pymem.exception.MemoryReadError:
            initialized = False

    print("\n[Movement Worker] Восстанавливаю оригинальные значения...")
    try:
        _, movement_comp_ptr = get_pointers(pm, base_address)
        if movement_comp_ptr and initialized:
            pm.write_uchar(movement_comp_ptr + MOVEMENT_MODE_OFFSET, MOVE_WALKING)
            pm.write_float(movement_comp_ptr + MAX_WALK_SPEED_OFFSET, original_values["walk_speed"])
            pm.write_float(movement_comp_ptr + MAX_FLY_SPEED_OFFSET, original_values["fly_speed"])
            pm.write_float(movement_comp_ptr + AIR_CONTROL_OFFSET, original_values["air_control"])
            pm.write_float(movement_comp_ptr + GRAVITY_SCALE_OFFSET, original_values["gravity"])
            pm.write_float(movement_comp_ptr + WALKABLE_FLOOR_ANGLE_OFFSET, original_values["floor_angle"])
            print("[Movement Worker] Значения восстановлены.")
    except:
        print("[Movement Worker] Не удалось восстановить значения.")

def read_fstring(pm, address):
    try:
        ptr = pm.read_longlong(address)
        if not ptr: return ""
        length = pm.read_int(address + 8)
        if not (0 < length < 128): return ""
        raw = pm.read_bytes(ptr, length * 2)
        return raw.decode('utf-16', errors='ignore').strip('\x00')
    except:
        return ""

def world_to_screen(world_location, cam_loc, cam_rot, fov, screen_width, screen_height):
    try:
        v_delta = (world_location[0] - cam_loc[0], world_location[1] - cam_loc[1], world_location[2] - cam_loc[2])
        yaw, pitch, roll = math.radians(cam_rot[1]), math.radians(cam_rot[0]), math.radians(cam_rot[2])
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        matrix = ((cp*cy,cp*sy,sp),(math.sin(roll)*sp*cy-math.cos(roll)*sy,math.sin(roll)*sp*sy+math.cos(roll)*cy,-math.sin(roll)*cp),(-(math.cos(roll)*sp*cy)-math.sin(roll)*sy,-(math.cos(roll)*sp*sy)+math.sin(roll)*cy,math.cos(roll)*cp))
        v_transformed = (v_delta[1]*matrix[0][1]+v_delta[0]*matrix[0][0]+v_delta[2]*matrix[0][2], v_delta[1]*matrix[1][1]+v_delta[0]*matrix[1][0]+v_delta[2]*matrix[1][2], v_delta[1]*matrix[2][1]+v_delta[0]*matrix[2][0]+v_delta[2]*matrix[2][2])
        if v_transformed[0] < 0.1: return None
        screen_center_x, screen_center_y = screen_width/2, screen_height/2
        screen_x = screen_center_x + v_transformed[1] * (screen_center_x/math.tan(math.radians(fov)/2))/v_transformed[0]
        screen_y = screen_center_y - v_transformed[2] * (screen_center_x/math.tan(math.radians(fov)/2))/v_transformed[0]
        return int(screen_x), int(screen_y)
    except (ValueError, ZeroDivisionError, OverflowError): return None

def wh_scanner(pm, base_address):
    global wh_known_targets
    while not stop_event.is_set():
        if not cheat_states["wallhack"]:
            time.sleep(1)
            continue
        
        pawn_to_display = {}
        try:
            world_ptr = pm.read_longlong(base_address + GWORLD)
            level_ptr = pm.read_longlong(world_ptr + PERSISTENT_LEVEL)
            actors_array_ptr = pm.read_longlong(level_ptr + ACTORS_ARRAY)
            actor_count = pm.read_int(level_ptr + ACTORS_ARRAY + 0x8)
            
            for i in range(actor_count):
                try:
                    actor_ptr = pm.read_longlong(actors_array_ptr + i * 0x8)
                    if not actor_ptr: continue
                    ps_ptr = pm.read_longlong(actor_ptr + PLAYER_STATE_IN_PAWN_OFFSET)
                    if ps_ptr:
                        player_name = read_fstring(pm, ps_ptr + PLAYER_NAME_OFFSET)
                        if player_name:
                             pawn_to_display[actor_ptr] = player_name
                except pymem.exception.MemoryReadError: continue
            wh_known_targets = pawn_to_display
        except (pymem.exception.MemoryReadError, TypeError): pass
        time.sleep(1)
    print("[WH Scanner] Поток сканера завершен.")

def wh_drawer(pm, base_address):
    global wh_targets_on_screen
    game_hwnd = win32gui.FindWindow(GAME_WINDOW_CLASS, None)
    if not game_hwnd:
        print("[WH] Окно игры не найдено!")
        return
    rect = win32gui.GetWindowRect(game_hwnd)
    screen_width, screen_height = rect[2] - rect[0], rect[3] - rect[1]

    while not stop_event.is_set():
        if not cheat_states["wallhack"]:
            wh_targets_on_screen = []
            time.sleep(0.1)
            continue
        
        try:
            world_ptr = pm.read_longlong(base_address + GWORLD)
            game_instance_ptr = pm.read_longlong(world_ptr + OWNING_GAME_INSTANCE)
            local_players_array_ptr = pm.read_longlong(game_instance_ptr + LOCAL_PLAYERS)
            local_player_ptr = pm.read_longlong(local_players_array_ptr)
            player_controller_ptr = pm.read_longlong(local_player_ptr + PLAYER_CONTROLLER)
            camera_manager_ptr = pm.read_longlong(player_controller_ptr + PLAYER_CAMERA_MANAGER_OFFSET)
            pov_addr = camera_manager_ptr + CAMERA_CACHE_OFFSET + POV_OFFSET
            cam_loc = struct.unpack('ddd', pm.read_bytes(pov_addr + 0x0, 24))
            cam_rot = struct.unpack('ddd', pm.read_bytes(pov_addr + 0x18, 24))
            cam_fov = pm.read_float(pov_addr + 0x30)
            player_pawn_ptr = pm.read_longlong(player_controller_ptr + ACKNOWLEDGED_PAWN)
            
            new_actors_list = []
            current_targets = dict(wh_known_targets)

            for actor_ptr, name in current_targets.items():
                if actor_ptr == player_pawn_ptr: continue
                try:
                    root_comp_ptr = pm.read_longlong(actor_ptr + ROOT_COMPONENT)
                    actor_loc = struct.unpack('ddd', pm.read_bytes(root_comp_ptr + RELATIVE_LOCATION, 24))
                    screen_pos = world_to_screen(actor_loc, cam_loc, cam_rot, cam_fov, screen_width, screen_height)
                    if screen_pos:
                        new_actors_list.append((*screen_pos, name))
                except (pymem.exception.MemoryReadError, struct.error): continue
            wh_targets_on_screen = new_actors_list
        except (pymem.exception.MemoryReadError, TypeError): pass
        time.sleep(0.001)
    print("[WH Drawer] Поток отрисовки завершен.")

def wh_gui_worker():
    root = tk.Tk()
    try:
        game_hwnd = win32gui.FindWindow(GAME_WINDOW_CLASS, None)
        rect = win32gui.GetWindowRect(game_hwnd)
        root.geometry(f"{rect[2]-rect[0]}x{rect[3]-rect[1]}+{rect[0]}+{rect[1]}")
    except: root.geometry("800x600")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", "black")
    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    def update_canvas():
        canvas.delete("all")
        if cheat_states["wallhack"]:
            for x, y, name in wh_targets_on_screen:
                canvas.create_oval(x-3, y-3, x+3, y+3, fill="cyan", outline="cyan")
                canvas.create_text(x, y - 10, text=name, fill="cyan", font=("Arial", 9, "bold"), anchor="s")
        if stop_event.is_set():
            root.destroy()
        else:
            root.after(16, update_canvas)

    root.after(16, update_canvas)
    root.mainloop()
    print("[WH GUI] Окно GUI закрыто.")

def main():
    global wh_gui_thread, wh_scanner_thread

    try:
        pm = pymem.Pymem(PROCESS_NAME)
        base_address = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME).lpBaseOfDll
    except pymem.exception.ProcessNotFound:
        print(f"❌ Игра '{PROCESS_NAME}' не найдена. Нажмите Enter для выхода.")
        input()
        return

    movement_thread = threading.Thread(target=movement_cheats_worker, args=(pm, base_address), daemon=True)
    movement_thread.start()

    wh_scanner_thread = threading.Thread(target=wh_scanner, args=(pm, base_address), daemon=True)
    wh_scanner_thread.start()
    wh_drawer_thread = threading.Thread(target=wh_drawer, args=(pm, base_address), daemon=True)
    wh_drawer_thread.start()
    
    print_menu()

    while not stop_event.is_set():
        if keyboard.is_pressed(KEY_FLY_MODE):
            cheat_states["fly_mode"] = not cheat_states["fly_mode"]
            print_menu()
            time.sleep(0.2)
        if keyboard.is_pressed(KEY_SUPER_SPEED):
            cheat_states["super_speed"] = not cheat_states["super_speed"]
            print_menu()
            time.sleep(0.2)
        if keyboard.is_pressed(KEY_SPIDERMAN):
            cheat_states["spiderman"] = not cheat_states["spiderman"]
            print_menu()
            time.sleep(0.2)
        if keyboard.is_pressed(KEY_AIR_CONTROL):
            cheat_states["air_control"] = not cheat_states["air_control"]
            print_menu()
            time.sleep(0.2)
        if keyboard.is_pressed(KEY_WALLHACK):
            cheat_states["wallhack"] = not cheat_states["wallhack"]
            if cheat_states["wallhack"] and (wh_gui_thread is None or not wh_gui_thread.is_alive()):
                wh_gui_thread = threading.Thread(target=wh_gui_worker, daemon=True)
                wh_gui_thread.start()
            print_menu()
            time.sleep(0.2)

        if keyboard.is_pressed(KEY_EXIT):
            print("\nПолучен сигнал на выход...")
            stop_event.set()
        
        time.sleep(0.05)

    print("Завершение работы потоков...")
    movement_thread.join()
    wh_scanner_thread.join()
    wh_drawer_thread.join()
    if wh_gui_thread:
        wh_gui_thread.join()
    print("✅ Программа успешно завершена.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nВыход по Ctrl+C...")
        stop_event.set()
