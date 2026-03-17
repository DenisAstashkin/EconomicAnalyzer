class Candle:
    def __init__(
        self, 
        low: float, 
        high: float,
        open: float,
        close: float,
        volume: int,
        date_time: str
        ):
        
        self.low = low
        self.high = high
        self.open = open
        self.close = close        
        self.volume = volume
        self.date_time = date_time