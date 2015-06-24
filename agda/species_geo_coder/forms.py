from django import forms

class SpeciesGeoCoderForm(forms.Form):
    name = forms.CharField(max_length=100, initial='SpeciesGeoCoder job', help_text='Job name')
    localities = forms.FileField(
            help_text='Select a file containing locality data',
            label='Localities', 
            required=True)
    polygons = forms.FileField(
            help_text='Select a file containing polygon data',
            label='Polygons', 
            required=True)
    occurences = forms.IntegerField(
            help_text='Specify the minimum number of occurrences (localities) needed for considering a species to be present in a polygon.',
            initial=1,
            required=False,
            min_value=1,
            label='Occurence cutoff')
    verbose = forms.BooleanField(
            help_text='Checking this box will make SpeciesGeoCoder also report how many times a species is found in each polygon.',
            required=False,
            label='Verbose')
    plot = forms.BooleanField(
            help_text='In addition to the occurrence result in NEXUS format, this function will make SpecieGeoCoder also produce graphical output that illustrates coexistance of species, distribution etc. This function is only available for datasets containing XX or less taxon names.',
            required=False,
            label='Make plots')
