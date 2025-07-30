from abc import abstractmethod

class State:

    def __init__(self, game_handler):
        self.handler = game_handler

    def update(self):

        self.sub_update()

    @abstractmethod
    def sub_update(self):
        pass
