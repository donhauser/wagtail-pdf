

from functools import wraps
from wagtail.contrib.routable_page.models import route


def route_function(func, pattern, *args, **kwargs):
    """
    Adds the @route decorator to func
    """
    
    @wraps(func) 
    @route(pattern, *args, **kwargs)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    
    return inner
    
