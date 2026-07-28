class InvalidUsage(Exception): # Custom exception class inheriting from standard Exception
    status_code = 400 # Default HTTP status code for bad requests

    # Initialize error details
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    # Serialize error details into a dictionary for JSON responses
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message

        return rv # Return formatted response payload