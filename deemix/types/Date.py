class Date(object):
    def __init__(self, year="XXXX", month="00", day="00"):
        self.year = year
        self.month = month
        self.day = day
        self.fixDayMonth()

    # Fix incorrect day month when detectable
    def fixDayMonth(self):
        if int(self.month) > 12:
            monthTemp = self.month
            self.month = self.day
            self.day = monthTemp

    def format(self, template):
        elements = {
            'year': ['YYYY', 'YY', 'Y'],
            'month': ['MM', 'M'],
            'day': ['DD', 'D']
        }
        for element, placeholders in elements.items():
            for placeholder in placeholders:
                if placeholder in template:
                    template = template.replace(placeholder, str(getattr(self, element)))
        return template
