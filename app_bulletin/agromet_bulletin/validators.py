from django.core.exceptions import ValidationError









def validate_integer_list(value):
    if not isinstance(value, list):
        raise ValidationError('This field must be a list.')
    for item in value:
        if not isinstance(item, int):
            raise ValidationError(f'All items in the list must be integers. Invalid item: {item}')
