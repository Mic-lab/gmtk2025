class Timer:

    def __init__(self, duration):
        self.duration = duration
        self.reset()

    def reset(self):
        self.frame = 0
        self.done = False

    def update(self):
        self.frame += 1
        self.done = self.frame == self.duration

    def get_ease_squared(self):
        # return 1 - (1 - self.frame) ** 2
        return 1 - (1 - self.ratio) ** 2

    @property
    def ratio(self):
        return self.frame / self.duration

    def __repr__(self):
        return f'<Timer({self.frame}/{self.duration})>'

    @staticmethod
    def update_timers(timers):
        new_timers = []
        for timer in timers:
            if not timer.done:
                new_timers.append(timer)
            timer.update()
        return new_timers
