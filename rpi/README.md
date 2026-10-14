# rpi — Raspberry Pi 4 (centralni računar)

Ubuntu Server 22.04 + PREEMPT_RT kernel + ROS 2 Humble. Strategija, obrada lidara,
planiranje i komunikacija sa Nucleo-om i Pico-om preko USB-a.

Kompletna konfiguracija i obrazloženja: log book **"Podešavanje Pi"** (`docs/podesavanje-pi.md`).

## Struktura

```
rpi/
├── system/                  konfiguracija operativnog sistema (sve što je u log book-u)
│   ├── setup.sh             primenjuje celu konfiguraciju, bezbedno ga je pokretati više puta
│   ├── udev/99-eurobot.rules   /dev/nucleo, /dev/pico, /dev/lidar
│   └── systemd/             servisi (CPU governor, kasnije autostart robota)
└── ros2/                    ROS 2 paketi (colcon)
    └── eurobot_bringup/     launch fajlovi i parametri (config/robot.yaml)
```

Paketi koji slede: `nucleo_bridge` (C++, RT nit), `pico_bridge`, `eurobot_msgs`, strategija.

## Prvo podešavanje na RPi-ju

```bash
# 1. kloniranje (vidi "Pristup GitHub-u" ispod)
git clone git@github.com:<ORGANIZACIJA>/Robot-2027.git ~/Robot-2027
cd ~/Robot-2027

# 2. konfiguracija sistema (prvo pogledaj šta bi uradio)
sudo DRY_RUN=1 ./rpi/system/setup.sh
sudo ./rpi/system/setup.sh
sudo reboot
```

RT kernel i ROS 2 se instaliraju ručno, po koracima 2 i 8 iz log book-a.

## Build

Uvek iz korena repozitorijuma. `protocol/` se gradi zajedno sa ROS paketima jer ga oni koriste.

```bash
cd ~/Robot-2027
source /opt/ros/humble/setup.bash
rosdep install --from-paths protocol rpi --ignore-src -y
colcon build --base-paths protocol rpi --symlink-install
source install/setup.bash
ros2 launch eurobot_bringup robot.launch.py
```

`build/`, `install/` i `log/` su u `.gitignore`. Ostali folderi (nucleo, pico, sima, beacon)
imaju `COLCON_IGNORE`, pa ih colcon preskače i kada se pokrene bez `--base-paths`.

## Rad na robotu (branch workflow)

```bash
cd ~/Robot-2027
git fetch
git switch feature/moja-funkcionalnost
colcon build --base-paths protocol rpi --symlink-install
./tools/flash_nucleo.sh            # ako je menjan i Nucleo firmware
# testiranje na robotu
```

Kada ništa ne radiš na robotu, RPi neka bude na `main`, da sledeća osoba krene od poznatog stanja.

## Pristup GitHub-u sa RPi-ja

Repo je privatan, pa RPi mora da se autentifikuje. Dve opcije:

- **SSH agent forwarding (preporučeno):** poveži se sa `ssh -A pi@kik`. Git na RPi-ju tada koristi
  *tvoj* ključ sa laptopa, pa push radi pod tvojim imenom, a na RPi-ju nema ničijih privatnih ključeva.
- **Deploy key (samo čitanje):** jedan ključ na RPi-ju, dodat u *Settings → Deploy keys* repozitorijuma.
  RPi može da radi `pull`, ali ne i `push`.

RPi je zajednički nalog, pa commit sa njega navodi autora eksplicitno:

```bash
git commit --author="Ime Prezime <mail@primer.com>" -m "poruka"
```

Bolje je izmene praviti na laptopu, a na RPi-ju samo `pull` i testirati.
