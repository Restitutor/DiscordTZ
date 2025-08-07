import copy


class DeepCopier(type):
    def __getattribute__(cls, name: str) -> object:
        return copy.deepcopy(super().__getattribute__(name))


class ErrorCode(metaclass=DeepCopier):
    OK = [200, "OK"]
    BAD_REQUEST = [400, "Bad Request"]
    FORBIDDEN = [403, "Forbidden"]
    NOT_FOUND = [404, "Not Found"]
    BAD_METHOD = [405, "Bad Method"]
    INTERNAL_SERVER_ERROR = [500, "Internal Server Error"]
    CONFLICT = [409, "Conflict"]
