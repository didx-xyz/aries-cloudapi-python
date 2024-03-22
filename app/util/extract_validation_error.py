from pydantic import ValidationError


def extract_validation_error_msg(e: ValidationError):
    output = ""
    for error in e.errors():
        field = error["loc"][0]  # Problematic field
        msg = error["msg"]  # msg is prefaced with: "Value error, <what we want>"
        msg_without_value_error = msg.split(", ", maxsplit=1)[1] if ", " in msg else msg
        output += f"{field} {msg_without_value_error}\n"
    return output.strip()
