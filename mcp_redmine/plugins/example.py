import codecs

DESCRIPTION = '''
    rot13: If True, applies ROT13 encoding to the response (default: False)

Returns:'''

def redmine_request(fn, args, kwargs):
    # Modify the description to add rot13 parameter documentation before Returns section
    parts = kwargs["description"].split('Returns:')
    kwargs['description'] = parts[0].rstrip() + DESCRIPTION + parts[1]

    # Create wrapper function that adds rot13 parameter with explicit signature
    def fn2(path: str, method: str = 'get', data: dict = None, params: dict = None, rot13: bool = False) -> str:
        # Call original function without rot13 parameter
        result = fn(path=path, method=method, data=data, params=params)

        # Apply ROT13 if requested
        if rot13:
            result = codecs.encode(result, 'rot_13')

        return result

    # Copy selected attributes from original function but keep our signature
    fn2.__name__ = fn.__name__
    fn2.__qualname__ = fn.__qualname__
    fn2.__module__ = fn.__module__
    fn2.__doc__ = kwargs['description']

    return fn2, args, kwargs
