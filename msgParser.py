class MsgParser:
    def __init__(self):
        pass

    def parse(self, str_sensors):
        sensors = {}
        b_open = str_sensors.find('(')

        while b_open >= 0:
            b_close = str_sensors.find(')', b_open)
            if b_close >= 0:
                substr = str_sensors[b_open + 1: b_close]
                items = substr.split()
                if len(items) >= 2:
                    value = [items[i] for i in range(1, len(items))]
                    sensors[items[0]] = value
                b_open = str_sensors.find('(', b_close)
        return sensors

    def stringify(self, dictionary):
        msg = ''
        for key, value in dictionary.items():
            if value and value[0] is not None:
                msg += f'({key}'
                for val in value:
                    msg += f' {str(val)}'
                msg += ')'
        return msg