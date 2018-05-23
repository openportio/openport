from openport.pyqrnative.PyQRNative import QRCode, QRErrorCorrectLevel

def get_qr_image(data):
    qr = QRCode(5, QRErrorCorrectLevel.L)
    qr.addData(data)
    qr.make()
    im = qr.makeImage()
    return im
