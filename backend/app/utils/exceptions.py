class APIException(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(APIException):
    def __init__(self, message):
        super().__init__(message, status_code=400)

class ResourceNotFound(APIException):
    def __init__(self, message):
        super().__init__(message, status_code=404)