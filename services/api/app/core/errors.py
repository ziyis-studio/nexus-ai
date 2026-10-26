class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(code)


def not_found() -> AppError:
    return AppError(404, "NOT_FOUND", "The resource is unavailable in this workspace.")
