from ..pyqrnative.PyQRNative import *


data = "http://www.baconsalt.com"

typeNumber = QRUtil.getBCHTypeInfo(len(data))
print typeNumber

qr = QRCode(5, QRErrorCorrectLevel.L)
qr.addData(data)
qr.make()

im = qr.makeImage()

im.show()