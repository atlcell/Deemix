#!/usr/bin/env python3

class QueueItem:
    def __init__(self, id=None, bitrate=None, title=None, artist=None, cover=None, size=None, type=None, settings=None, queueItemList=None):
        if queueItemList:
            self.title = queueItemList['title']
            self.artist = queueItemList['artist']
            self.cover = queueItemList['cover']
            self.size = queueItemList['size']
            self.type = queueItemList['type']
            self.id = queueItemList['id']
            self.bitrate = queueItemList['bitrate']
            self.settings = queueItemList['settings']
        else:
            self.title = title
            self.artist = artist
            self.cover = cover
            self.size = size
            self.type = type
            self.id = id
            self.bitrate = bitrate
            self.settings = settings
        self.downloaded = 0
        self.failed = 0
        self.errors = []
        self.progress = 0
        self.uuid = f"{self.type}_{self.id}_{self.bitrate}"
        self.cancel = False

    def toDict(self):
        return {
            'title': self.title,
            'artist': self.artist,
            'cover': self.cover,
            'size': self.size,
            'downloaded': self.downloaded,
            'failed': self.failed,
            'errors': self.errors,
            'progress': self.progress,
            'type': self.type,
            'id': self.id,
            'bitrate': self.bitrate,
            'uuid': self.uuid
        }

    def getResettedItem(self):
        item = self.toDict()
        item['downloaded'] = 0
        item['failed'] = 0
        item['progress'] = 0
        item['errors'] = []
        return item

    def getSlimmedItem(self):
        light = self.toDict()
        propertiesToDelete = ['single', 'collection', '_EXTRA']
        for property in propertiesToDelete:
            if property in light:
                del light[property]
        return light

class QISingle(QueueItem):
    def __init__(self, id=None, bitrate=None, title=None, artist=None, cover=None, type=None, settings=None, single=None, queueItemList=None):
        if queueItemList:
            super().__init__(queueItemList=queueItemList)
            self.single = queueItemList['single']
        else:
            super().__init__(id, bitrate, title, artist, cover, 1, type, settings)
            self.single = single

    def toDict(self):
        queueItem = super().toDict()
        queueItem['single'] = self.single
        return queueItem

class QICollection(QueueItem):
    def __init__(self, id=None, bitrate=None, title=None, artist=None, cover=None, size=None, type=None, settings=None, collection=None, queueItemList=None):
        if queueItemList:
            super().__init__(queueItemList=queueItemList)
            self.collection = queueItemList['collection']
        else:
            super().__init__(id, bitrate, title, artist, cover, size, type, settings)
            self.collection = collection

    def toDict(self):
        queueItem = super().toDict()
        queueItem['collection'] = self.collection
        return queueItem

class QIConvertable(QICollection):
    def __init__(self, id=None, bitrate=None, title=None, artist=None, cover=None, size=None, type=None, settings=None, extra=None, queueItemList=None):
        if queueItemList:
            super().__init__(queueItemList=queueItemList)
            self.extra = queueItemList['_EXTRA']
        else:
            super().__init__(id, bitrate, title, artist, cover, size, type, settings, [])
            self.extra = extra

    def toDict(self):
        queueItem = super().toDict()
        queueItem['_EXTRA'] = self.extra
        return queueItem
