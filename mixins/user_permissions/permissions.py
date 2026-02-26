#  import project constant
from ffwc_django_project.project_constant import SESAME_USERS
sesame_user_role = SESAME_USERS['roles']








class CustomUserPermission:
    def super_admin(req):  
        user = req.user 

        p_list = []
        for role in user.role.all(): 
            p_list.append(role.name)     
        if sesame_user_role[1] in p_list:
            return True
        return False
    
    def country_admin(req): 
        user = req.user 

        p_list = []
        for role in user.role.all(): 
            p_list.append(role.name)     
        if sesame_user_role[2] in p_list:
            return True
        return False
    
    def general_user(req):  
        user = req.user 

        p_list = []
        for role in user.role.all(): 
            p_list.append(role.name)     
        if sesame_user_role[3] in p_list:
            return True
        return False