
CONNECT_CLIENT_EVENT = 0x00
RECEIVE_ECHO = 0x01
DISCONNECTED_CLIENT_EVENT = 0x02
ORDER_FETCH_EVENT = 0x03
RESULT_FETCH_EVENT = 0x04


# https://stackoverflow.com/questions/7492068/python-class-decorator-arguments

def event_handler(function):
    def wrapper(*args, **kwargs):
        function(*args, **kwargs)

    return wrapper


_handlers = {}


def register_handler(code, handler):
    # if not type(handler) is _event_handler:
    #     raise Exception("이벤트 함수가 아닙니다")

    if not code in _handlers:
        _handlers[code] = []

    _handlers[code].append(handler)


def remove_handler(code, handler):
    # if not type(handler) is event_handler:
    #     raise Exception("이벤트 함수가 아닙니다")

    if not code in _handlers:
        raise Exception('등록된 이벤트가 아닙니다.')

    group = _handlers[code]

    for i in range(len(group)):
        print(i)
        if group[i] == handler:
            del group[i]
            return

    raise Exception('등록되지 않은 헨들러입니다.')


def call_handler(code: int,
                 **kwargs):
    if not code in _handlers:
        return

    for handler in _handlers[code]:
        handler(kwargs)
