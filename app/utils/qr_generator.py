import qrcode
import base64
import socket
from io import BytesIO

def get_local_ip():
    """Discover the local network IP address (e.g. 192.168.x.x)."""
    try:
        # Create a dummy socket to a public DNS server to determine routing IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # connect() for UDP doesn't actually send packets
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return '127.0.0.1'

def generate_qr_base64(data: str) -> str:
    """
    Generates a QR code for the given data and returns it as a base64 encoded PNG string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
