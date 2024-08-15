import argparse
import inspect
from typing import Any, Callable, get_args, get_origin, Union


def create_argparse_from_function(func: Callable[..., Any]) -> None:
    """
    Creates an ArgumentParser from a function and uses it to parse command-line arguments.

    The function's parameters are used to create arguments for the ArgumentParser. Parameters with default
    values are created as optional arguments, and parameters without default values are created as positional
    arguments. The type hints of the parameters are used to determine the type of the arguments, and the
    metadata of the type hints (if present) are used as the help text for the arguments.

    For example: `name: Annotated[str, "The name of the person"]`
    Do not use bools as optional arguments. They are used as flags, so they are technically always optional, defaulting to false.
    Do not use unions
    All function parameters must be either bool, str, int, float, or Annotated[T, desc] where T is any of the previous

    After the arguments are parsed, the function is called with the parsed arguments.

    Args:
        func: The function to create an ArgumentParser from.
    """
    signature = inspect.signature(func)
    parser = argparse.ArgumentParser(description=func.__doc__)
    for name, param in signature.parameters.items():
        param_type = param.annotation
        description = None
        if hasattr(param_type, '__metadata__'):
            description = param_type.__metadata__[0]
            param_type = param_type.__origin__
        # Unwrap Optional[T] to T
        if get_origin(param_type) is Union:
            param_type = next(t for t in get_args(param_type) if t is not type(None))

        if param.default == inspect.Parameter.empty:
            parser.add_argument(name, type=param_type, help=description)
        else:
            if param_type == bool:
                parser.add_argument('--' + name, action='store_true', help=description)
            else:
                parser.add_argument('--' + name, type=param_type, default=param.default, help=description)

    args = parser.parse_args()
    func(**vars(args))
