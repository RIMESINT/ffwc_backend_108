########################################################################
### START LOOKUP
########################################################################

from django.db.models import Transform
class LowerCase(Transform):
    lookup_name = "lower"
    function = "LOWER"
    bilateral = True

from django.db.models import CharField, TextField
CharField.register_lookup(LowerCase)
TextField.register_lookup(LowerCase)

########################################################################
### END LOOKUP
########################################################################