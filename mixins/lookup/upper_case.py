########################################################################
### START LOOKUP
########################################################################

from django.db.models import Transform
class UpperCase(Transform):
    lookup_name = "upper"
    function = "UPPER"
    bilateral = True

from django.db.models import CharField, TextField
CharField.register_lookup(UpperCase)
TextField.register_lookup(UpperCase)

########################################################################
### END LOOKUP
########################################################################