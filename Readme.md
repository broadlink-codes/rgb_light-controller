# 🎛️ RGB Lights Control via Broadlink IR Device

Control your RGB lights using a Broadlink IR device with smart features like sound spike detection and screen color syncing.

## ✨ Features

- **Sound Spike Trigger**  
  Detects sudden spikes in ambient sound using microphone and triggers the RGB lights with a color that has the most contrast on the screen at that moment.

- **TV Backlight Sync**  
  Matches your TV backlight color with the dominant color on your screen.  
  _Note: The syncing is functional but not yet perfectly smooth._

---

## 🚀 Getting Started

### 1. Run Broadlink API

Clone and run the [Broadlink API](https://github.com/broadlink-codes/broadlink-api):

> ⚠️ **Note:** The Broadlink API **must always be running**

---

### 2. Configure Your Remote

Inside the `config/` folder:

- `remote_code.json`  
  Contains function names mapped to IR packets.

- `color_mapping.py`  
  Maps each remote button to an RGB value.

#### Learn IR Commands

To configure your own device:

1. Use Postman (or a similar tool) to call the Broadlink API’s `/api/learn` endpoint.
2. Point your remote at the Broadlink device and press the desired button.
3. Copy the returned IR pulse packet.
4. Add the IR packet to `remote_code.json` like the existing samples.
5. Update `color_mapping.py` with the RGB value for each button.

---

## ⚙️ Configuration

Edit the main configuration in `./config.json`:

```json
{
  "SPIKE_MONITOR_CONFIG": {
    "sample_rate": 44100,
    "chunk_size": 1024,
    "spike_threshold": 8,
    "channels": 1
  },
  "SCREEN_MONITOR_CONFIG": {
    "display_id": 1,
    "save_images": false
  },
  "BACKLIGHT_CONFIG": {
    "display_id": 1,
    "interval": 1,
    "duration": null,
    "save_images": false
  }
}
```

- `spike_threshold`: Set this according to room noise to avoid false triggers.
- `display_id`: Select which screen to monitor for color syncing.
- `save_images`: Optionally save screen captures for debugging.

---

## 🔐 Required Environment Variables

| Variable         | Description                                  |
|------------------|----------------------------------------------|
| `BROADLINK_API_URL`    | (get it from the docker running)         |

---

## 🔄 Running Features

### Start Backlight Feature
```bash
python run_backlight_feature.py
```

### Start Spike Feature
```bash
python run_spike_feature.py
```

---

## 🚨 Notes
- Make sure your RGB lights are properly configured before running the features.
- Broadlink API should be up and running at all times.

---

## 🙌 Contributions
Feel free to contribute by improving the color detection, optimizing performance, or supporting additional devices!

---

## ✅ License
MIT License

