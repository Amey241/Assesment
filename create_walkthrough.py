"""Create a short animated walkthrough of the local support-chat demo."""
from PIL import Image, ImageDraw, ImageFont
import textwrap

W, H = 1200, 800
FONT = "C:/Windows/Fonts/segoeui.ttf"
BOLD = "C:/Windows/Fonts/segoeuib.ttf"

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)

def multiline(draw, pos, text, width, size=21, color="#14251e", bold=False, gap=8):
    f = font(size, bold)
    lines = []
    for part in text.split("\n"):
        lines += textwrap.wrap(part, width=width) or [""]
    x, y = pos
    for line in lines:
        draw.text((x, y), line, font=f, fill=color)
        y += size + gap
    return y

def frame(messages, input_text="", typing=False):
    im = Image.new("RGB", (W, H), "#fbfaf6")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((130, 55, 1070, 745), 20, fill="#ffffff", outline="#d9e2dc", width=2)
    d.rounded_rectangle((160, 80, 208, 128), 15, fill="#155e4b")
    d.text((176, 88), "A", font=font(25, True), fill="white")
    d.text((225, 86), "Aster & Row Support", font=font(29, True), fill="#14251e")
    rounded(d, (907, 91, 1035, 121), 15, "#e8f4ee", "#b9dfcc")
    d.text((928, 97), "●  Online", font=font(14, True), fill="#185b43")
    d.line((130, 150, 1070, 150), fill="#d9e2dc", width=2)
    d.text((160, 166), "Support conversation", font=font(17, True), fill="#14251e")
    d.text((800, 167), "Private & session-only", font=font(14), fill="#627069")
    y = 205
    for who, text, kind, sources in messages:
        is_user = kind == "user"
        x = 600 if is_user else 165
        box_w = 410 if is_user else 590
        wrapped = [line for part in text.split("\n") for line in (textwrap.wrap(part, width=44 if is_user else 65) or [""])]
        box_h = 58 + len(wrapped) * 29 + (31 if sources else 0)
        fill = "#eef5ff" if is_user else ("#e8f4ee" if kind == "welcome" else "#f5f7f5")
        rounded(d, (x, y, x + box_w, y + box_h), 15, fill, "#d4e2f5" if is_user else "#e2e8e3")
        d.text((x+18, y+14), who, font=font(15, True), fill="#14251e")
        end = multiline(d, (x+18, y+38), text, 44 if is_user else 65, 18, "#14251e", False, 7)
        if sources:
            d.text((x+18, end+4), "Sources: " + sources, font=font(13), fill="#627069")
        y += box_h + 15
    if typing:
        d.text((166, y+6), "Support is checking the available information…", font=font(16), fill="#627069")
    d.line((130, 630, 1070, 630), fill="#d9e2dc", width=2)
    chips = ["Where is ORD-1007?", "How long to return a backpack?", "Do you ship to Canada?"]
    cx = 160
    for chip in chips:
        tw = d.textlength(chip, font=font(13)) + 24
        rounded(d, (cx, 647, cx+tw, 677), 15, "#f6f8f6", "#d9e2dc")
        d.text((cx+12, 654), chip, font=font(13), fill="#254338")
        cx += tw + 8
    rounded(d, (160, 690, 1038, 730), 14, "#ffffff", "#c8d5cc", 2)
    d.text((176, 700), input_text or "Ask about an order or policy…", font=font(16), fill="#627069" if not input_text else "#14251e")
    rounded(d, (967, 697, 1028, 723), 9, "#155e4b")
    d.text((979, 701), "Send", font=font(12, True), fill="white")
    return im

welcome = [("Welcome to Aster & Row", "How can I help today? I can check an order with its ID or explain our policies.", "welcome", "")]
order_question = welcome + [("You", "Where is ORD-1007?", "user", "")]
order_answer = order_question + [("Aster & Row Support", "Your order is shipped. The order is in transit with UPS and is currently estimated to arrive on August 22, 2026.", "agent", "")]
canada_question = welcome + [("You", "Do you ship to Canada?", "user", "")]
canada_answer = canada_question + [("Aster & Row Support", "Canada is supported. Orders generally arrive 5–9 business days after dispatch; duties, taxes, and brokerage charges are not prepaid.", "agent", "06-international-shipping.md — Supported destinations")]

frames = [
    frame(welcome), frame(welcome, "Where is ORD-1007?"), frame(order_question, typing=True),
    frame(order_answer), frame(welcome), frame(welcome, "Do you ship to Canada?"), frame(canada_question, typing=True), frame(canada_answer)
]
durations = [1800, 1200, 1200, 3300, 700, 1200, 1200, 3500]
frames[0].save("aster-row-walkthrough.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
print("Created aster-row-walkthrough.gif")
