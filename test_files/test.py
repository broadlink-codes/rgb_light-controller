import argparse

from utils.screen_monitor_2 import monitor_screen
from utils.light_manager import LightManager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor the most prominent color on screen")
    parser.add_argument("-i", "--interval", type=float, default=1.0,
                      help="Time between screen captures in seconds (default: 1.0)")
    parser.add_argument("-d", "--duration", type=float, default=None,
                      help="Total monitoring duration in seconds (default: indefinite)")
    parser.add_argument("-s", "--screen", type=int, default=None,
                      help="Screen ID to capture (default: primary screen)")
    parser.add_argument("--save", action="store_true",
                      help="Save captured images to the 'screen_captures' directory")
    
    args = parser.parse_args()
    
    display_text = f"Screen {args.screen}" if args.screen is not None else "the primary screen"
    save_text = " and saving images" if args.save else ""
    print(f"Starting screen color monitoring on {display_text}{save_text} (interval: {args.interval}s)")
    print("Press Ctrl+C to stop")

    light_manager = LightManager(
        device_name="monitor_backlight",
        initial_brightness=9,
    )
    
    light_manager.execute_commands(["on"])
    monitor_screen(args.interval, light_manager, args.screen, args.duration, args.save)