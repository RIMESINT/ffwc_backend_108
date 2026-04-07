from django import forms
from data_load.models import Station,RainfallStation
import datetime

class StationChoiceField(forms.ModelChoiceField):
    """Custom field to display 'Name (Code)' in the dropdown"""
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.station_code})"


class HydroSyncForm(forms.Form):
    # Setting empty_label to '*' and required=False makes it the default 'All' option
    station = StationChoiceField(
        queryset=Station.objects.filter(status=True).order_by('name'),
        label="Select Station",
        empty_label="* (All Stations)",
        required=False,
        initial=None
    )
    
    from_date = forms.DateField(
        label="Start Date (From Date)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today() - datetime.timedelta(days=7)
    )
    to_date = forms.DateField(
        label="End Date (To date)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today()
    )
    
    mode = forms.ChoiceField(
        label="Sync Mode",
        choices=[('update', 'Update'), ('fill_missing', 'Fill Missing')],
        initial='update',
        widget=forms.RadioSelect
    )


class HourlySyncForm(forms.Form):
    station = StationChoiceField(
        queryset=Station.objects.filter(status=True).order_by('name'),
        label="Select Station",
        empty_label="* (All Stations)",
        required=False
    )
    # Hour range (e.g., 24, 48, 72)
    hours = forms.IntegerField(
        label="Hour Range (e.g. 72)", 
        initial=72, 
        min_value=1, 
        max_value=168 # 1 week limit
    )
    mode = forms.ChoiceField(
        label="Sync Mode",
        choices=[('update', 'Update'), ('fill_missing', 'Fill Missing')],
        initial='update',
        widget=forms.RadioSelect
    )




class RainfallStationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.station_code})"

class RainfallSyncForm(forms.Form):
    station = RainfallStationChoiceField(
        queryset=RainfallStation.objects.filter(status=True).order_by('name'),
        label="Select Rainfall Station",
        empty_label="* (All Stations)",
        required=False
    )
    from_date = forms.DateField(
        label="Start Date (From Date)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today() - datetime.timedelta(days=7)
    )
    to_date = forms.DateField(
        label="End Date (To date)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=datetime.date.today()
    )
    mode = forms.ChoiceField(
        choices=[('update', 'Update'), ('fill_missing', 'Fill Missing')],
        initial='update',
        widget=forms.RadioSelect
    )

class RainfallHourlySyncForm(forms.Form):
    # Fix: Point to RainfallStation instead of WaterLevel Station
    station = RainfallStationChoiceField(
        queryset=RainfallStation.objects.filter(status=True).order_by('name'),
        label="Select Rainfall Station",
        empty_label="* (All Stations)",
        required=False,
        initial=None
    )
    
    hours = forms.IntegerField(
        label="Hour Range (e.g. 72)", 
        initial=24, 
        min_value=1, 
        max_value=168 
    )
    
    mode = forms.ChoiceField(
        label="Sync Mode",
        choices=[('update', 'Update'), ('fill_missing', 'Fill Missing')],
        initial='update',
        widget=forms.RadioSelect
    )



class SMSSyncForm(forms.Form):
    source = forms.CharField(label="Source Number", initial="01751330394")
    date_from = forms.DateField(label="Date From", widget=forms.DateInput(attrs={'type': 'date'}), initial=datetime.date.today() - datetime.timedelta(days=30))
    date_to = forms.DateField(label="Date To", widget=forms.DateInput(attrs={'type': 'date'}), initial=datetime.date.today())