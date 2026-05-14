import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import uuid
import os

def round_corners(image, radius):
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    image.putalpha(mask)
    return image

class QRService:
    @staticmethod
    def generate_qr_code(data: str, version: int = 1, box_size: int = 10, border: int = 2) -> Image.Image:
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Konvertiere Hex-Farbe zu RGB Tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def generate_sticker_with_design(
        qr_image: Image.Image,
        design: str = "default",
        label: str = "",
        title: str = "",
        logo_path: str = None,
        background_color: str = "#f5f5f5"
    ) -> Image.Image:

        if design == "default":
            return QRService._create_default_sticker(qr_image, label, logo_path, title, background_color)
        elif design == "minimal":
            return QRService._create_minimal_sticker(qr_image, label, background_color)
        elif design == "professional":
            return QRService._create_professional_sticker(qr_image, label, title, logo_path, background_color)
        else:
            return qr_image

    @staticmethod
    def _create_default_sticker(qr_image: Image.Image, label: str = "", logo_path: str = None, title: str = "", background_color: str = "#f5f5f5") -> Image.Image:
        qr_size = 330
        qr_resized = qr_image.resize((qr_size, qr_size))

        sticker_width = 400
        sticker_height = 520
        bg_rgb = QRService._hex_to_rgb(background_color)
        sticker = Image.new("RGB", (sticker_width, sticker_height), bg_rgb)

        x_offset = (sticker_width - qr_size) // 2
        y_offset = 55
        sticker.paste(qr_resized, (x_offset, y_offset))

        draw = ImageDraw.Draw(sticker)
        draw.rectangle([(10, 10), (sticker_width-10, sticker_height-10)], outline=(100, 150, 200), width=2)

        # Verwende title parameter, fallback auf default Text
        text = title if title else "Kontakt via QR"

        # Versuche mit kleinerer Schrift zu schreiben
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 7)
        except:
            font_small = ImageFont.load_default()

        # Teile Text in zwei Zeilen falls nötig
        if len(text) > 12:  # Umbruch bei > 12 Zeichen
            words = text.split()
            if len(words) >= 2:  # Wenn mindestens 2 Worte: nach Wort-Grenze brechen
                mid = len(words) // 2
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
            else:  # Sonst: in der Mitte brechen
                mid = len(text) // 2
                line1 = text[:mid]
                line2 = text[mid:]

            bbox1 = draw.textbbox((0, 0), line1, font=font_small)
            bbox2 = draw.textbbox((0, 0), line2, font=font_small)
            x1 = (sticker_width - (bbox1[2] - bbox1[0])) // 2
            x2 = (sticker_width - (bbox2[2] - bbox2[0])) // 2
            draw.text((x1, 13), line1, fill="black", font=font_small)
            draw.text((x2, 23), line2, fill="black", font=font_small)
        else:
            bbox = draw.textbbox((0, 0), text, font=font_small)
            x = (sticker_width - (bbox[2] - bbox[0])) // 2
            draw.text((x, 18), text, fill="black", font=font_small)

        # Label: Nur anzeigen wenn vorhanden, mit größerer Font
        if label:
            try:
                font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
            except:
                font_label = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), label, font=font_label)
            x = (sticker_width - (bbox[2] - bbox[0])) // 2
            draw.text((x, 400), label, fill="black", font=font_label)

        # Füge grünes Telefon-Icon unten ein
        try:
            phone_icon = Image.open(os.path.join(os.path.dirname(__file__), "..", "phone_icon.png"))
            icon_size = 40
            phone_resized = phone_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            icon_x = (sticker_width - icon_size) // 2
            icon_y = 455
            sticker.paste(phone_resized, (icon_x, icon_y), phone_resized)
        except:
            # Fallback: Zeichne einfaches Icon wenn Datei nicht vorhanden
            QRService._draw_phone_icon(draw, sticker_width // 2 - 15, 465, size=30, color=(0, 180, 0))

        return sticker

    @staticmethod
    def _create_minimal_sticker(qr_image: Image.Image, label: str = "", background_color: str = "#f5f5f5") -> Image.Image:
        qr_size = 300
        qr_resized = qr_image.resize((qr_size, qr_size))
        bg_rgb = QRService._hex_to_rgb(background_color)
        sticker = Image.new("RGB", (qr_size + 40, qr_size + 80), bg_rgb)
        sticker.paste(qr_resized, (20, 20))

        draw = ImageDraw.Draw(sticker)
        draw.rectangle([(10, 10), (qr_size + 30, qr_size + 70)], outline=(200, 200, 200), width=1)

        # Grünes Telefon-Icon unten
        try:
            phone_icon = Image.open(os.path.join(os.path.dirname(__file__), "..", "phone_icon.png"))
            icon_size = 36
            phone_resized = phone_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            icon_x = ((qr_size + 40) - icon_size) // 2
            icon_y = qr_size + 28
            sticker.paste(phone_resized, (icon_x, icon_y), phone_resized)
        except:
            QRService._draw_phone_icon(draw, (qr_size + 40) // 2 - 15, qr_size + 32, size=28, color=(0, 180, 0))

        return sticker

    @staticmethod
    def _create_professional_sticker(
        qr_image: Image.Image,
        label: str = "",
        title: str = "",
        logo_path: str = None,
        background_color: str = "#1e1e1e"
    ) -> Image.Image:
        size = 500
        bg_rgb = QRService._hex_to_rgb(background_color)
        sticker = Image.new("RGB", (size, size), bg_rgb)
        draw = ImageDraw.Draw(sticker)

        # Weißer Rahmen statt schwarzem Ring
        draw.rectangle([(10, 10), (size-10, size-10)], outline="white", width=3)

        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            font_large = ImageFont.load_default()

        if title:
            # Prüfe ob Text zu lang ist und teile auf 2 Zeilen auf
            if len(title) > 12 and '\n' not in title:
                words = title.split()
                if len(words) >= 2:
                    mid = len(words) // 2
                    lines = [" ".join(words[:mid]), " ".join(words[mid:])]
                else:
                    # Sonst: in der Mitte brechen
                    mid = len(title) // 2
                    lines = [title[:mid], title[mid:]]
            else:
                lines = title.split('\n') if '\n' in title else [title]

            title_y = 25
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font_large)
                text_width = bbox[2] - bbox[0]
                x_pos = (size - text_width) // 2
                draw.text((x_pos, title_y), line, font=font_large, fill="white")
                title_y += 50
        else:
            bbox = draw.textbbox((0, 0), "CONTACT", font=font_large)
            text_width = bbox[2] - bbox[0]
            x_pos = (size - text_width) // 2
            draw.text((x_pos, 25), "CONTACT", font=font_large, fill="white")

            bbox = draw.textbbox((0, 0), "CARAVAN/RV", font=font_large)
            text_width = bbox[2] - bbox[0]
            x_pos = (size - text_width) // 2
            draw.text((x_pos, 75), "CARAVAN/RV", font=font_large, fill="white")

        qr_size = 200
        qr_resized = qr_image.resize((qr_size, qr_size))
        qr_border = 10
        white_bg = Image.new("RGB", (qr_size + qr_border*2, qr_size + qr_border*2), "white")
        white_bg.paste(qr_resized, (qr_border, qr_border))

        qr_x = (size - qr_size - qr_border*2) // 2
        qr_y = 150
        sticker.paste(white_bg, (qr_x, qr_y))

        try:
            phone_icon = Image.open("phone_icon.png")
            icon_size = 60
            phone_resized = phone_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            icon_x = size - icon_size - 20
            icon_y = size - icon_size - 20
            sticker.paste(phone_resized, (icon_x, icon_y), phone_resized)
        except:
            pass

        return sticker

    @staticmethod
    def _draw_phone_icon(draw, x, y, size=30, color=(0, 180, 0)):
        """Zeichnet ein grünes Telefon-Icon"""
        # Äußerer Rahmen (Telefon-Körper)
        draw.rectangle(
            [(x, y), (x + size, y + size)],
            fill=color,
            outline=color,
            width=1
        )

        # Heller Bildschirm-Bereich in der Mitte
        screen_margin = 3
        screen_color = (100, 255, 100)  # Helles Grün für Kontrast
        draw.rectangle(
            [(x + screen_margin, y + screen_margin),
             (x + size - screen_margin, y + int(size * 0.7))],
            fill=screen_color,
            outline=screen_color,
            width=1
        )

        # Kleine Sprechmuschel (unten im Telefon)
        mouth_y = y + int(size * 0.75)
        draw.ellipse(
            [(x + int(size * 0.3), mouth_y),
             (x + int(size * 0.7), mouth_y + int(size * 0.15))],
            fill=color,
            outline=color,
            width=1
        )

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())[:12]
