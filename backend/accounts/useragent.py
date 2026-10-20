"""
Dependency-free User-Agent -> device label parser.

Order matters: Edge/Chrome/Safari UA strings are nested (Edge contains "Chrome"
and "Safari"; Chrome contains "Safari"), so the most specific token is checked
first. This is a labeling aid only — never a security control.
"""


def parse_device_name(ua):
    if not ua:
        return "Unknown device"
    s = ua.lower()

    if "windows" in s:
        os_ = "Windows"
    elif "iphone" in s:
        os_ = "iPhone"
    elif "ipad" in s:
        os_ = "iPad"
    elif "android" in s:
        os_ = "Android"
    elif "mac os x" in s or "macintosh" in s:
        os_ = "macOS"
    elif "cros" in s:
        os_ = "ChromeOS"
    elif "linux" in s:
        os_ = "Linux"
    else:
        os_ = "Unknown OS"

    if "edg/" in s:
        br = "Edge"
    elif "opr/" in s or "opera" in s:
        br = "Opera"
    elif "chrome" in s and "chromium" not in s:
        br = "Chrome"
    elif "firefox" in s:
        br = "Firefox"
    elif "safari" in s:
        br = "Safari"
    else:
        br = "Unknown browser"

    return f"{br} on {os_}"[:255]
