class Picture:
    def __init__(self, md5="", type=None, url=None):
        self.md5 = md5
        self.type = type
        self.url = url

    def generatePictureURL(self, size, format):
        if self.url: return self.url
        if format.startswith("jpg"):
            if '-' in format:
                quality = format[4:]
            else:
                quality = 80
            format = 'jpg'
            return "https://e-cdns-images.dzcdn.net/images/{}/{}/{}x{}-{}".format(
                self.type,
                self.md5,
                size, size,
                f'000000-{quality}-0-0.jpg'
            )
        if format == 'png':
            return "https://e-cdns-images.dzcdn.net/images/{}/{}/{}x{}-{}".format(
                self.type,
                self.md5,
                size, size,
                'none-100-0-0.png'
            )
