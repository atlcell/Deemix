import binascii
from Cryptodome.Cipher import Blowfish, AES
from Cryptodome.Hash import MD5

def _md5(data):
    h = MD5.new()
    h.update(str.encode(data) if isinstance(data, str) else data)
    return h.hexdigest()

def generateBlowfishKey(trackId):
    SECRET = 'g4el58wc' + '0zvf9na1'
    idMd5 = _md5(trackId)
    bfKey = ""
    for i in range(16):
        bfKey += chr(ord(idMd5[i]) ^ ord(idMd5[i + 16]) ^ ord(SECRET[i]))
    return bfKey

def generateStreamURL(sng_id, md5, media_version, format):
    urlPart = b'\xa4'.join(
        [str.encode(md5), str.encode(str(format)), str.encode(str(sng_id)), str.encode(str(media_version))])
    md5val = _md5(urlPart)
    step2 = str.encode(md5val) + b'\xa4' + urlPart + b'\xa4'
    step2 = step2 + (b'.' * (16 - (len(step2) % 16)))
    urlPart = binascii.hexlify(AES.new(b'jo6aey6haid2Teih', AES.MODE_ECB).encrypt(step2))
    return "https://e-cdns-proxy-" + md5[0] + ".dzcdn.net/mobile/1/" + urlPart.decode("utf-8")

def reverseStreamURL(url):
    urlPart = url[42:]
    step2 = AES.new(b'jo6aey6haid2Teih', AES.MODE_ECB).decrypt(binascii.unhexlify(urlPart.encode("utf-8")))
    (md5val, md5, format, sng_id, media_version, _) = step2.split(b'\xa4')
    return (sng_id.decode('utf-8'), md5.decode('utf-8'), media_version.decode('utf-8'), format.decode('utf-8'))
