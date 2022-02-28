class SavedThread():
    def __init__(self, i, own, ti):
        self.index = i
        self.owner = own
        self.time = ti
        self.mustContinue = True
        