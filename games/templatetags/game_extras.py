from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Lookup dictionary[key] safely in a template.
    """
    return dictionary.get(key, "")
