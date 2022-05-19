class SavedThread():
    def __init__(self, i, own, ti):
        self.index = i
        self.owner = own
        self.time = ti
        self.mustContinue = True

    def __str__(self):
        return ( 'id: ' + str(self.owner) + '\n' +
                 'index: ' + str(self.index) + '\n' +
                 'time: ' + str(self.time) + '\n' +
                 'cont: ' + str(self.mustContinue) + '\n'
                )