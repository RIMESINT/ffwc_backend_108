from django import forms
from django.contrib.admin import FieldListFilter
from datetime import date, timedelta
from django.db.models import Q
from data_load.models import Station
from django.utils.translation import gettext_lazy as _


class StationNameFilter(FieldListFilter):
    title = 'Station Name'
    template = 'admin/station_name_filter.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        stations = Station.objects.all().order_by('name')
        self.choices = [(station.id, station.name) for station in stations]

    def expected_parameters(self):
        return ['station_name']

    def queryset(self, request, queryset):
        if request.GET.get('station_name'):
            return queryset.filter(station_id__id=request.GET.get('station_name'))
        return queryset
    
    def lookups(self, request, model_admin):
        return []
    
    def has_output(self):
        return True


class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    end_date = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

class WaterLevelDateFilter(FieldListFilter):
    title = 'By Observation Date'
    template = 'admin/water_level_date_filter.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.form = DateRangeForm(request.GET)
        self.request = request  # Store the request object

    def expected_parameters(self):
        return ['start_date', 'end_date', 'date']

    def queryset(self, request, queryset):
        today = date.today()

        if request.GET.get('date') == 'today':
            return queryset.filter(observation_date__date=today)
        if request.GET.get('date') == 'last_7_days':
            return queryset.filter(observation_date__date__gte=today - timedelta(days=7))
        if request.GET.get('date') == 'this_month':
            return queryset.filter(observation_date__year=today.year, observation_date__month=today.month)
        if request.GET.get('date') == 'this_year':
            return queryset.filter(observation_date__year=today.year)

        if self.form.is_valid():
            start_date = self.form.cleaned_data.get('start_date')
            end_date = self.form.cleaned_data.get('end_date')
            if start_date:
                queryset = queryset.filter(observation_date__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(observation_date__date__lte=end_date)
        return queryset

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('last_7_days', 'Last 7 Days'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
        ]
    
    def choices(self, cl):
        # Use the stored request object
        all_selected = not ('date' in self.request.GET or 'start_date' in self.request.GET or 'end_date' in self.request.GET)
        yield {
            'selected': all_selected,
            'query_string': cl.get_query_string({}, ['date', 'start_date', 'end_date']),
            'display': 'All',
        }
        
        for lookup, title in self.lookups(self.request, cl.model_admin):
            yield {
                'selected': self.request.GET.get('date') == lookup,
                'query_string': cl.get_query_string({'date': lookup}, ['date', 'start_date', 'end_date']),
                'display': title,
            }

    def has_output(self):
        return True