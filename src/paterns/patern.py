class Patern:
    BASE_WEIGHTS = {#словарь весов
        "star": 90, 
        "engulfing": 80, 
        "soldiers": 70,  
        "doji": 30       
    }
    
    def __init__(self, name):
        if name not in self.BASE_WEIGHTS:
            raise Exception('[ERROR] Name missing')
                             
        self.name = name
        self.weight = self.BASE_WEIGHTS[name]
        
    def change_weight(self, ratio):#если встречается вместе с другими патернами
        if ratio <= 0: raise Exception('[ERROR] Division err')
        self.weight = self.weight/ratio 