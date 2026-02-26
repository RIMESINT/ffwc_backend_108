from rest_framework.pagination import PageNumberPagination

from ffwc_django_project.project_constant import PAGINATION_CONSTANT








class StandardResultsSetPagination(PageNumberPagination):
    page_size = PAGINATION_CONSTANT['page_size']
    page_size_query_param = PAGINATION_CONSTANT['page_size_query_param']
    max_page_size = PAGINATION_CONSTANT['max_page_size'] 


class PaginationSetup:
    def pagination_details(request):
        limit = 10
        page = 1 

        if (('page' in request.GET) and (int(request.GET['page']) != 0) and (int(request.GET['page']) != None)):
            page = int(request.GET['page'])

        if (('limit' in request.GET) and (int(request.GET['limit']) != 0) and (int(request.GET['limit']) != None)):
            limit = int(request.GET['limit'])

        if ('limit' in request.GET) and (int(request.GET['limit']) > 100):
            limit = 100

        if ('limit' in request.GET) and (int(request.GET['limit']) < 0):
            limit = 10

        if ('page' in request.GET) and (int(request.GET['page']) < 0):
            page = 1

        offset = (limit * (int(request.GET['page']) - 1))

        # print("offset: ", offset)
        # print("limit: ", limit)

        return {"page": page, "limit": limit, "offset": offset}

    def custom_standard_pagination(page_size):
        return type("SubClass", (StandardResultsSetPagination,), {"page_size": page_size})