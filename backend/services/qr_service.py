import qrcode
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from io import BytesIO
from PIL import Image, ImageDraw
import uuid

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
    def generate_sticker_with_design(
        qr_image: Image.Image,
        design: str = "default",
        label: str = "",
        logo_path: str = None
    ) -> Image.Image:

        if design == "default":
            return QRService._create_default_sticker(qr_image, label, logo_path)
        elif design == "minimal":
            return QRService._create_minimal_sticker(qr_image, label)
        elif design == "professional":
            return QRService._create_professional_sticker(qr_image, label, logo_path)
        else:
            return qr_image

    @staticmethod
    def _create_default_sticker(qr_image: Image.Image, label: str = "", logo_path: str = None) -> Image.Image:
        qr_size = 300
        qr_resized = qr_image.resize((qr_size, qr_size))

        sticker_width = 400
        sticker_height = 500
        sticker = Image.new("RGB", (sticker_width, sticker_height), "white")

        x_offset = (sticker_width - qr_size) // 2
        y_offset = 80
        sticker.paste(qr_resized, (x_offset, y_offset))

        draw = ImageDraw.Draw(sticker)
        text = "Kontakt via QR"
        try:
            draw.text((sticker_width // 2 - 50, 30), text, fill="black")
        except:
            draw.text((sticker_width // 2 - 30, 30), text, fill="black")

        if label:
            try:
                draw.text((sticker_width // 2 - 60, 420), label, fill="gray")
            except:
                draw.text((sticker_width // 2 - 30, 420), label, fill="gray")

        return sticker

    @staticmethod
    def _create_minimal_sticker(qr_image: Image.Image, label: str = "") -> Image.Image:
        qr_size = 300
        qr_resized = qr_image.resize((qr_size, qr_size))
        sticker = Image.new("RGB", (qr_size + 40, qr_size + 40), "white")
        sticker.paste(qr_resized, (20, 20))
        return sticker

    @staticmethod
    def _create_professional_sticker(
        qr_image: Image.Image,
        label: str = "",
        logo_path: str = None
    ) -> Image.Image:
        qr_size = 280
        qr_resized = qr_image.resize((qr_size, qr_size))

        sticker_width = 450
        sticker_height = 550
        sticker = Image.new("RGB", (sticker_width, sticker_height), "white")

        draw = ImageDraw.Draw(sticker)
        draw.rectangle([(10, 10), (sticker_width-10, sticker_height-10)], outline="black", width=3)

        x_offset = (sticker_width - qr_size) // 2
        y_offset = 100
        sticker.paste(qr_resized, (x_offset, y_offset))

        try:
            draw.text((sticker_width // 2 - 80, 30), "FAHRZEUG-KONTAKT", fill="black")
        except:
            pass

        if label:
            try:
                draw.text((sticker_width // 2 - 60, 450), label, fill="black")
            except:
                pass

        return sticker

    @staticmethod
    def generate_unique_id() -> str:
        return str(uuid.uuid4())[:12]
